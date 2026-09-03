"""FastAPI web adapter for Document Builder."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from hashoej_document_builder.core.artifacts import ArtifactManager
from hashoej_document_builder.core.conditions import is_field_active
from hashoej_document_builder.core.discovery import (
    discover_enabled_templates,
)
from hashoej_document_builder.core.errors import (
    DocumentRenderingError,
    PDFConversionError,
    PDFConversionUnavailableError,
    TemplateNotFoundError,
)
from hashoej_document_builder.core.models import GenerationSession, TemplatePackage
from hashoej_document_builder.core import pdf, rendering
from hashoej_document_builder.core.session import SessionStore
from hashoej_document_builder.core.validation import (
    get_field_display_label,
    get_initial_repeater_row,
    get_initial_values,
    parse_form_data,
    sanitize_step_input,
    validate_all_steps_values,
    validate_step_values,
)

COOKIE_NAME = "document_builder_session_id"
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME_TYPE = "application/pdf"


def _is_https(request: Request) -> bool:
    """Check if the request was made over HTTPS directly at the ASGI layer."""
    return request.url.scheme == "https"


def _get_active_field_ids(form_definition: dict[str, Any], values: dict[str, Any]) -> set[str]:
    """Return the set of field IDs that are currently active under show_when rules."""
    active_ids: set[str] = set()
    for step in form_definition.get("steps", []):
        for field in step.get("fields", []):
            if is_field_active(field, values):
                active_ids.add(field["id"])
    return active_ids


def create_app(
    template_root: Path | str | None = None,
    session_store: SessionStore | None = None,
    clock: Callable[[], datetime] | None = None,
    artifact_manager: ArtifactManager | None = None,
    soffice_cmd: str | None = None,
) -> FastAPI:
    """Application factory for Document Builder."""
    app = FastAPI(title="Document Builder")

    # Paths
    base_dir = Path(__file__).resolve().parent
    templates_dir = base_dir / "templates"
    static_dir = base_dir / "static"

    # Services
    root_path = Path(template_root) if template_root else Path("templates")
    if session_store is not None:
        store = session_store
    else:
        store = SessionStore(now_fn=clock) if clock is not None else SessionStore()

    if artifact_manager is not None:
        art_mgr = artifact_manager
    else:
        art_mgr = ArtifactManager(now_fn=clock) if clock is not None else ArtifactManager()

    def is_option_match(opt_val: Any, selected_val: Any) -> bool:
        if type(opt_val) is bool or type(selected_val) is bool:
            return (type(opt_val) is type(selected_val)) and (opt_val == selected_val)
        if isinstance(selected_val, (list, tuple, set)):
            return any(type(opt_val) is type(item) and opt_val == item for item in selected_val)
        return (type(opt_val) is type(selected_val)) and (opt_val == selected_val)

    templates = Jinja2Templates(directory=str(templates_dir))
    # Register display helper filter for select/radio/multiselect option labels
    templates.env.filters["display_label"] = get_field_display_label
    templates.env.globals["get_field_display_label"] = get_field_display_label
    templates.env.globals["is_option_match"] = is_option_match

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    def _get_template(template_id: str) -> TemplatePackage | None:
        """Find an enabled template package by ID."""
        try:
            enabled_list = discover_enabled_templates(root_path)
            for pkg in enabled_list:
                if pkg.id == template_id:
                    return pkg
            return None
        except TemplateNotFoundError:
            return None

    def _get_session(request: Request) -> GenerationSession | None:
        """Retrieve active session from cookie, extending TTL on access."""
        session_id = request.cookies.get(COOKIE_NAME)
        if not session_id:
            return None
        return store.get(session_id, touch=True)

    def _get_template_for_session(session: GenerationSession) -> TemplatePackage | None:
        """Find the template bound to the session, enforcing ID and exact version match."""
        pkg = _get_template(session.template_id)
        if pkg is None or pkg.version != session.template_version:
            # Delete stale or version-mismatched session
            store.delete(session.session_id)
            return None
        return pkg

    @app.get("/health")
    def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        """Render the homepage listing available templates."""
        try:
            available_templates = discover_enabled_templates(root_path)
        except TemplateNotFoundError:
            available_templates = []
        return templates.TemplateResponse(
            request=request,
            name="home.html",
            context={
                "templates": available_templates,
            },
        )

    @app.get("/templates/{template_id}", response_class=HTMLResponse)
    def document_intro(template_id: str, request: Request) -> HTMLResponse:
        """Render the introduction page for a document template."""
        pkg = _get_template(template_id)
        if pkg is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Dokumenttype ikke fundet",
                    "error_message": "Den valgte dokumentskabelon er enten deaktiveret eller findes ikke.",
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return templates.TemplateResponse(
            request=request,
            name="intro.html",
            context={
                "template": pkg,
            },
        )

    @app.post("/templates/{template_id}/start")
    def start_journey(template_id: str, request: Request) -> Response:
        """Create a new GenerationSession and begin the wizard journey."""
        pkg = _get_template(template_id)
        if pkg is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skabelon ikke fundet eller ikke aktiv.",
            )

        initial_values = get_initial_values(pkg.form_definition)
        session = store.create(
            template_id=pkg.id,
            template_version=pkg.version,
            initial_values=initial_values,
            initial_step=0,
        )

        response = RedirectResponse(url="/journey/step/0", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key=COOKIE_NAME,
            value=session.session_id,
            httponly=True,
            samesite="lax",
            secure=_is_https(request),
        )
        return response

    @app.get("/journey/step/{step_idx}", response_class=HTMLResponse)
    def get_step(step_idx: int, request: Request) -> Response:
        """Render a specific step of the wizard journey."""
        session = _get_session(request)
        if session is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Session udløbet",
                    "error_message": "Din aktive session er udløbet efter inaktivitet eller findes ikke. Start venligst forfra fra forsiden.",
                },
                status_code=status.HTTP_200_OK,
            )

        pkg = _get_template_for_session(session)
        if pkg is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Skabelon ikke tilgængelig",
                    "error_message": "Skabelonen er opdateret eller ikke længere tilgængelig. Start venligst forfra.",
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        steps = pkg.form_definition.get("steps", [])
        total_steps = len(steps)

        # Progression check: GET requests cannot access future locked steps
        if step_idx < 0:
            return RedirectResponse(url="/journey/step/0", status_code=status.HTTP_303_SEE_OTHER)
        if step_idx > session.current_step:
            # Direct access to locked future step is redirected to current unlocked step
            target = min(session.current_step, total_steps - 1)
            return RedirectResponse(url=f"/journey/step/{target}", status_code=status.HTTP_303_SEE_OTHER)
        if step_idx >= total_steps:
            return RedirectResponse(url="/journey/review", status_code=status.HTTP_303_SEE_OTHER)

        step_def = steps[step_idx]
        step_id = step_def["id"]

        # Display values: authoritative session values overlaid with step draft if present
        display_values = dict(session.values)
        if step_id in session.draft_values:
            display_values.update(session.draft_values[step_id])

        return templates.TemplateResponse(
            request=request,
            name="wizard_step.html",
            context={
                "template": pkg,
                "step": step_def,
                "step_index": step_idx,
                "total_steps": total_steps,
                "values": display_values,
                "errors": {},
            },
        )

    @app.post("/journey/step/{step_idx}", response_class=HTMLResponse)
    async def post_step(step_idx: int, request: Request) -> Response:
        """Handle submission of a wizard step."""
        session = _get_session(request)
        if session is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Session udløbet",
                    "error_message": "Din aktive session er udløbet efter inaktivitet. Start venligst forfra fra forsiden.",
                },
                status_code=status.HTTP_200_OK,
            )

        pkg = _get_template_for_session(session)
        if pkg is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Skabelon ikke tilgængelig",
                    "error_message": "Skabelonen er opdateret eller ikke længere tilgængelig. Start venligst forfra.",
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        steps = pkg.form_definition.get("steps", [])
        total_steps = len(steps)

        # Reject POST to locked future step
        if step_idx < 0:
            return RedirectResponse(url="/journey/step/0", status_code=status.HTTP_303_SEE_OTHER)
        if step_idx > session.current_step:
            target = min(session.current_step, total_steps - 1)
            return RedirectResponse(url=f"/journey/step/{target}", status_code=status.HTTP_303_SEE_OTHER)
        if step_idx >= total_steps:
            return RedirectResponse(url="/journey/review", status_code=status.HTTP_303_SEE_OTHER)

        step_def = steps[step_idx]
        step_id = step_def["id"]

        form = await request.form()
        raw_dict: dict[str, Any] = {}
        for key in form.keys():
            v_list = form.getlist(key)
            if len(v_list) > 1:
                raw_dict[key] = v_list
            else:
                raw_dict[key] = v_list[0]

        # Harden action parsing: only accept a single scalar string action
        action_list = form.getlist("action")
        if len(action_list) > 1 or (action_list and not isinstance(action_list[0], str)):
            # Duplicate or non-scalar action is rejected safely without mutating state
            return RedirectResponse(
                url=f"/journey/step/{step_idx}",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        action = action_list[0] if action_list else "next"

        parsed_submitted = parse_form_data(raw_dict)
        sanitized_submitted = sanitize_step_input(step_def, parsed_submitted)

        # 1. Back button: Save sanitized values to step draft without modifying authoritative values
        if action == "prev":
            session.draft_values[step_id] = sanitized_submitted
            store.save(session)
            if step_idx > 0:
                return RedirectResponse(
                    url=f"/journey/step/{step_idx - 1}",
                    status_code=status.HTTP_303_SEE_OTHER,
                )
            return RedirectResponse(
                url=f"/templates/{pkg.id}",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        # 2. Repeater Add Row action
        if action.startswith("repeater_add:"):
            parts = action.split(":", 1)
            rep_id = parts[1] if len(parts) > 1 else ""
            rep_def = next((f for f in step_def.get("fields", []) if f["id"] == rep_id and f.get("type") == "repeater"), None)
            if rep_def is not None:
                current_draft = dict(session.draft_values.get(step_id, {}))
                current_rows = list(sanitized_submitted.get(rep_id, current_draft.get(rep_id, session.values.get(rep_id, []))))
                max_items = rep_def.get("max_items")
                if max_items is None or len(current_rows) < max_items:
                    new_row = get_initial_repeater_row(rep_def)
                    current_rows.append(new_row)
                sanitized_submitted[rep_id] = current_rows
                session.draft_values[step_id] = sanitized_submitted
                store.save(session)
            return RedirectResponse(
                url=f"/journey/step/{step_idx}",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        # 3. Repeater Remove Row action
        if action.startswith("repeater_remove:"):
            parts = action.split(":")
            if len(parts) == 3:
                rep_id = parts[1]
                rep_def = next((f for f in step_def.get("fields", []) if f["id"] == rep_id and f.get("type") == "repeater"), None)
                if rep_def is not None:
                    try:
                        row_idx = int(parts[2])
                    except ValueError:
                        row_idx = -1
                    current_draft = dict(session.draft_values.get(step_id, {}))
                    current_rows = list(sanitized_submitted.get(rep_id, current_draft.get(rep_id, session.values.get(rep_id, []))))
                    if 0 <= row_idx < len(current_rows):
                        current_rows.pop(row_idx)
                    sanitized_submitted[rep_id] = current_rows
                    session.draft_values[step_id] = sanitized_submitted
                    store.save(session)
            return RedirectResponse(
                url=f"/journey/step/{step_idx}",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        # Reject any other unknown action safely without advancing or mutating authoritative state
        if action != "next":
            return RedirectResponse(
                url=f"/journey/step/{step_idx}",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        # 4. Next button: Authoritative server validation
        validation_res = validate_step_values(step_def, sanitized_submitted, session.values)

        if not validation_res.is_valid:
            # Save sanitized draft so Refresh preserves user input
            session.draft_values[step_id] = sanitized_submitted
            store.save(session)

            display_values = dict(session.values)
            display_values.update(sanitized_submitted)

            return templates.TemplateResponse(
                request=request,
                name="wizard_step.html",
                context={
                    "template": pkg,
                    "step": step_def,
                    "step_index": step_idx,
                    "total_steps": total_steps,
                    "values": display_values,
                    "errors": validation_res.errors,
                },
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            )

        # Step validation succeeded: commit authoritative coerced values and clear this step's draft
        session.values.update(validation_res.coerced_values)
        session.draft_values.pop(step_id, None)
        # Advance progression boundary
        session.current_step = max(session.current_step, step_idx + 1)
        store.save(session)

        if step_idx + 1 < total_steps:
            return RedirectResponse(
                url=f"/journey/step/{step_idx + 1}",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        return RedirectResponse(url="/journey/review", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/journey/review", response_class=HTMLResponse)
    def review(request: Request) -> Response:
        """Render the control/review page with all authoritative entered values."""
        session = _get_session(request)
        if session is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Session udløbet",
                    "error_message": "Din aktive session er udløbet efter inaktivitet. Start venligst forfra fra forsiden.",
                },
                status_code=status.HTTP_200_OK,
            )

        pkg = _get_template_for_session(session)
        if pkg is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Skabelon ikke tilgængelig",
                    "error_message": "Skabelonen er opdateret eller ikke længere tilgængelig. Start venligst forfra.",
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        steps = pkg.form_definition.get("steps", [])
        total_steps = len(steps)

        # Review is locked until all steps have been completed at least once
        if session.current_step < total_steps:
            target = min(session.current_step, total_steps - 1)
            return RedirectResponse(url=f"/journey/step/{target}", status_code=status.HTTP_303_SEE_OTHER)

        active_field_ids = _get_active_field_ids(pkg.form_definition, session.values)
        full_validation = validate_all_steps_values(pkg.form_definition, session.values)

        return templates.TemplateResponse(
            request=request,
            name="review.html",
            context={
                "template": pkg,
                "values": session.values,
                "errors": full_validation.errors,
                "active_field_ids": active_field_ids,
            },
        )

    @app.get("/journey/preview", response_class=HTMLResponse)
    def preview(request: Request) -> Response:
        """Render the semantic HTML preview page."""
        session = _get_session(request)
        if session is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Session udløbet",
                    "error_message": "Din aktive session er udløbet efter inaktivitet. Start venligst forfra fra forsiden.",
                },
                status_code=status.HTTP_200_OK,
            )

        pkg = _get_template_for_session(session)
        if pkg is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Skabelon ikke tilgængelig",
                    "error_message": "Skabelonen er opdateret eller ikke længere tilgængelig. Start venligst forfra.",
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        steps = pkg.form_definition.get("steps", [])
        total_steps = len(steps)

        # Progression check: must have completed all steps
        if session.current_step < total_steps:
            target = min(session.current_step, total_steps - 1)
            return RedirectResponse(url=f"/journey/step/{target}", status_code=status.HTTP_303_SEE_OTHER)

        # Authoritative full validation check
        full_validation = validate_all_steps_values(pkg.form_definition, session.values)
        if not full_validation.is_valid:
            return RedirectResponse(url="/journey/review", status_code=status.HTTP_303_SEE_OTHER)

        active_field_ids = _get_active_field_ids(pkg.form_definition, session.values)

        return templates.TemplateResponse(
            request=request,
            name="preview.html",
            context={
                "template": pkg,
                "values": session.values,
                "active_field_ids": active_field_ids,
            },
        )

    @app.post("/journey/generate/docx")
    def generate_docx_file(request: Request) -> Response:
        """Generate and download the authoritative DOCX document."""
        session = _get_session(request)
        if session is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Session udløbet",
                    "error_message": "Din aktive session er udløbet efter inaktivitet. Start venligst forfra fra forsiden.",
                },
                status_code=status.HTTP_200_OK,
            )

        pkg = _get_template_for_session(session)
        if pkg is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Skabelon ikke tilgængelig",
                    "error_message": "Skabelonen er opdateret eller ikke længere tilgængelig. Start venligst forfra.",
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        steps = pkg.form_definition.get("steps", [])
        total_steps = len(steps)

        # Progression check: must have completed all steps
        if session.current_step < total_steps:
            target = min(session.current_step, total_steps - 1)
            return RedirectResponse(url=f"/journey/step/{target}", status_code=status.HTTP_303_SEE_OTHER)

        # Validation gate
        full_val = validate_all_steps_values(pkg.form_definition, session.values)
        if not full_val.is_valid:
            return RedirectResponse(url="/journey/review", status_code=status.HTTP_303_SEE_OTHER)

        # Opportunistic artifact cleanup
        art_mgr.cleanup_stale_artifacts()

        # Build rendering context
        render_ctx = rendering.build_render_context(pkg.form_definition, session.values)
        temp_docx_path = art_mgr.create_artifact_path("docx")

        try:
            rendering.render_docx(pkg.document_template, render_ctx, temp_docx_path)
        except DocumentRenderingError:
            art_mgr.cleanup_artifact(temp_docx_path.parent)
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Dokumentgenerering fejlede",
                    "error_message": "Der opstod en fejl under oprettelsen af Word-dokumentet. Prøv venligst igen.",
                },
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        safe_filename = f"{pkg.id}.docx"
        bg = BackgroundTasks()
        bg.add_task(art_mgr.cleanup_artifact, temp_docx_path.parent)
        return FileResponse(
            path=temp_docx_path,
            media_type=DOCX_MIME_TYPE,
            filename=safe_filename,
            background=bg,
        )

    @app.post("/journey/generate/pdf")
    def generate_pdf_file(request: Request) -> Response:
        """Generate DOCX and convert to PDF for download."""
        session = _get_session(request)
        if session is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Session udløbet",
                    "error_message": "Din aktive session er udløbet efter inaktivitet. Start venligst forfra fra forsiden.",
                },
                status_code=status.HTTP_200_OK,
            )

        pkg = _get_template_for_session(session)
        if pkg is None:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Skabelon ikke tilgængelig",
                    "error_message": "Skabelonen er opdateret eller ikke længere tilgængelig. Start venligst forfra.",
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        steps = pkg.form_definition.get("steps", [])
        total_steps = len(steps)

        # Progression check: must have completed all steps
        if session.current_step < total_steps:
            target = min(session.current_step, total_steps - 1)
            return RedirectResponse(url=f"/journey/step/{target}", status_code=status.HTTP_303_SEE_OTHER)

        # Validation gate
        full_val = validate_all_steps_values(pkg.form_definition, session.values)
        if not full_val.is_valid:
            return RedirectResponse(url="/journey/review", status_code=status.HTTP_303_SEE_OTHER)

        # Opportunistic artifact cleanup
        art_mgr.cleanup_stale_artifacts()

        # Build rendering context
        render_ctx = rendering.build_render_context(pkg.form_definition, session.values)
        temp_docx_path = art_mgr.create_artifact_path("docx")

        try:
            rendering.render_docx(pkg.document_template, render_ctx, temp_docx_path)
        except DocumentRenderingError:
            art_mgr.cleanup_artifact(temp_docx_path.parent)
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "Dokumentgenerering fejlede",
                    "error_message": "Der opstod en fejl under oprettelsen af Word-dokumentet. Prøv venligst igen.",
                },
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            pdf_path = pdf.convert_docx_to_pdf(
                docx_path=temp_docx_path,
                output_dir=temp_docx_path.parent,
                soffice_cmd=soffice_cmd,
            )
        except PDFConversionUnavailableError:
            art_mgr.cleanup_artifact(temp_docx_path.parent)
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "PDF-konvertering ikke tilgængelig",
                    "error_message": "PDF-konvertering er ikke tilgængelig i dette miljø. Du kan stadig hente dit dokument som Word (DOCX).",
                    "show_docx_fallback": True,
                },
                status_code=status.HTTP_200_OK,
            )
        except PDFConversionError:
            art_mgr.cleanup_artifact(temp_docx_path.parent)
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error_title": "PDF-konvertering fejlede",
                    "error_message": "Der opstod en fejl under konvertering til PDF. Du kan stadig hente dit dokument som Word (DOCX).",
                    "show_docx_fallback": True,
                },
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        safe_filename = f"{pkg.id}.pdf"
        bg = BackgroundTasks()
        bg.add_task(art_mgr.cleanup_artifact, temp_docx_path.parent)
        return FileResponse(
            path=pdf_path,
            media_type=PDF_MIME_TYPE,
            filename=safe_filename,
            background=bg,
        )

    return app


# Default app instance for CLI / standard deployment
app = create_app()

"""DOCX rendering pipeline and render context assembly."""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any
import docxtpl

from hashoej_document_builder.core.conditions import is_field_active
from hashoej_document_builder.core.errors import DocumentRenderingError

logger = logging.getLogger(__name__)


def build_render_context(
    form_definition: dict[str, Any],
    values: dict[str, Any],
) -> dict[str, Any]:
    """Build an isolated rendering context dictionary from form definition and authoritative session values.

    Rules:
      - Active scalar/checkbox/date/select/radio/multiselect/repeater -> authoritative value.
      - Inactive field under show_when -> omitted/empty representation (no stale data leakage).
      - 'info' field -> never in render context.
      - Optional empty scalar -> empty string ("") or None for number.
      - Optional empty repeater/multiselect -> empty list ([]).
      - Booleans, numbers, dates, strings, lists preserved as exact Python types.
    """
    context: dict[str, Any] = {}

    for step in form_definition.get("steps", []):
        for field in step.get("fields", []):
            fid = field["id"]
            ftype = field.get("type")

            if ftype == "info":
                continue

            # Inactive field under current condition context
            if not is_field_active(field, values):
                if ftype == "checkbox":
                    context[fid] = False
                elif ftype in ("multiselect", "repeater"):
                    context[fid] = []
                elif ftype == "number":
                    context[fid] = None
                else:
                    context[fid] = ""
                continue

            # Active field
            val = values.get(fid)

            if ftype == "repeater":
                child_defs = [c for c in field.get("fields", []) if c.get("type") != "info"]
                raw_rows = val if isinstance(val, list) else []
                clean_rows: list[dict[str, Any]] = []

                for row in raw_rows:
                    row_dict = row if isinstance(row, dict) else {}
                    clean_row: dict[str, Any] = {}
                    for child in child_defs:
                        cid = child["id"]
                        ctype = child.get("type")
                        cval = row_dict.get(cid)
                        if cval is None:
                            if ctype == "checkbox":
                                clean_row[cid] = False
                            elif ctype == "multiselect":
                                clean_row[cid] = []
                            elif ctype == "number":
                                clean_row[cid] = None
                            else:
                                clean_row[cid] = ""
                        else:
                            clean_row[cid] = copy.deepcopy(cval)
                    clean_rows.append(clean_row)

                context[fid] = clean_rows

            elif ftype == "checkbox":
                context[fid] = bool(val)

            elif ftype == "multiselect":
                context[fid] = copy.deepcopy(val) if isinstance(val, list) else ([] if val is None else [val])

            elif ftype == "number":
                context[fid] = val if val is not None else None

            else:
                context[fid] = copy.deepcopy(val) if val is not None else ""

    return context


def render_docx(
    template_path: Path | str,
    context: dict[str, Any],
    output_path: Path | str,
) -> Path:
    """Render a DOCX template using docxtpl with safe XML escaping.

    Atomic: on failure, any partial output file is cleaned up and a DocumentRenderingError is raised.
    Form payloads and document contents are never logged.

    Returns:
        The Path to the rendered DOCX file.
    """
    tpl_path = Path(template_path).resolve()
    out_path = Path(output_path).resolve()

    if not tpl_path.is_file():
        raise DocumentRenderingError(f"DOCX template file not found: {tpl_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        tpl = docxtpl.DocxTemplate(str(tpl_path))
        # autoescape=True ensures all user strings are escaped as XML entities (<, >, &)
        tpl.render(context, autoescape=True)
        tpl.save(str(out_path))
    except Exception as exc:
        if out_path.exists():
            out_path.unlink(missing_ok=True)
        logger.error("DOCX template rendering failed: %s", type(exc).__name__)
        raise DocumentRenderingError(f"Failed to render DOCX template: {exc}") from exc

    return out_path

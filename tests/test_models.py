from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path
import pytest

from hashoej_document_builder.core.models import (
    GeneratedArtifact,
    GenerationSession,
    TemplatePackage,
)


def test_template_package_can_be_created() -> None:
    package = TemplatePackage(
        id="hif-01-role",
        version=1,
        enabled=True,
        title="Rollebeskrivelse",
        category="Organisation",
        description="Beskriv en rolle.",
        path=Path("/templates/hif-01-role"),
        form_definition={"steps": [{"id": "basic", "title": "Grundoplysninger"}]},
        document_template=Path("/templates/hif-01-role/document.docx"),
    )

    assert package.id == "hif-01-role"
    assert package.version == 1
    assert package.enabled is True
    assert package.title == "Rollebeskrivelse"
    assert package.category == "Organisation"
    assert package.description == "Beskriv en rolle."
    assert package.path == Path("/templates/hif-01-role")
    assert package.form_definition == {"steps": [{"id": "basic", "title": "Grundoplysninger"}]}
    assert package.document_template == Path("/templates/hif-01-role/document.docx")

    with pytest.raises(FrozenInstanceError):
        package.id = "hif-02-task"  # type: ignore[misc]


def test_generation_session_initialization_and_updates() -> None:
    session = GenerationSession(
        session_id="opaque-session-xyz123",
        template_id="hif-01-role",
        template_version=1,
        current_step=0,
    )

    assert session.session_id == "opaque-session-xyz123"
    assert session.template_id == "hif-01-role"
    assert session.template_version == 1
    assert session.current_step == 0
    assert session.values == {}
    assert isinstance(session.created_at, datetime)
    assert isinstance(session.last_activity_at, datetime)

    # Values and steps can be updated during the wizard flow
    session.values["role_name"] = "Formand"
    session.current_step = 1
    assert session.values == {"role_name": "Formand"}
    assert session.current_step == 1


def test_generated_artifact_can_be_created() -> None:
    artifact = GeneratedArtifact(
        filename="rollebeskrivelse.docx",
        format="docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        temporary_path=Path("/tmp/document_builder_artifacts/temp123/rollebeskrivelse.docx"),
    )

    assert artifact.filename == "rollebeskrivelse.docx"
    assert artifact.format == "docx"
    assert artifact.mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert artifact.temporary_path == Path("/tmp/document_builder_artifacts/temp123/rollebeskrivelse.docx")

    with pytest.raises(FrozenInstanceError):
        artifact.filename = "other.docx"  # type: ignore[misc]


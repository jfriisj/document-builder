from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TemplatePackage:
    id: str
    version: int
    enabled: bool
    title: str
    category: str
    description: str
    path: Path
    form_definition: dict[str, Any]
    document_template: Path


@dataclass
class GenerationSession:
    """Transient runtime state for a document generation journey.

    Attributes:
        session_id: Cryptographically random opaque session identifier.
        template_id: The bound template package ID.
        template_version: The bound template package version.
        current_step: Server-side forward progression boundary (0 .. total_steps).
            Represents the highest step unlocked by successful validation.
        values: Authoritative, validated, and type-coerced session data.
        draft_values: Temporary, sanitized uncommitted input data keyed by step ID.
        created_at: Timezone-aware UTC timestamp of session creation.
        last_activity_at: Timezone-aware UTC timestamp of most recent valid activity.
    """

    session_id: str
    template_id: str
    template_version: int
    current_step: int = 0
    values: dict[str, Any] = field(default_factory=dict)
    draft_values: dict[str, dict[str, Any]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    last_activity_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class GeneratedArtifact:
    filename: str
    format: str
    mime_type: str
    temporary_path: Path

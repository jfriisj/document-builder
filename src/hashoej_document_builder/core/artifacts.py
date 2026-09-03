"""Transient filesystem artifact management and opportunistic stale cleanup."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import secrets
import shutil
import tempfile

from hashoej_document_builder.core.models import utc_now

DEFAULT_ARTIFACT_TTL_MINUTES = 10
SUPPORTED_ARTIFACT_FORMATS = frozenset({"docx", "pdf"})
VALID_PREFIX_REGEX = re.compile(r"^[a-z0-9_]{1,16}$")


class ArtifactManager:
    """Manages short-lived temporary files for DOCX and PDF generation."""

    def __init__(
        self,
        temp_root: Path | str | None = None,
        ttl_minutes: int = DEFAULT_ARTIFACT_TTL_MINUTES,
        now_fn: Callable[[], datetime] = utc_now,
    ) -> None:
        if temp_root is not None:
            self._temp_root = Path(temp_root).resolve()
        else:
            self._temp_root = Path(tempfile.gettempdir()).resolve() / "document_builder_artifacts"

        self._ttl_minutes = ttl_minutes
        self._now = now_fn
        self._temp_root.mkdir(parents=True, exist_ok=True)

    @property
    def temp_root(self) -> Path:
        return self._temp_root

    def create_artifact_path(self, file_format: str, prefix: str = "art") -> Path:
        """Create a dedicated, unpredictable temporary sub-directory and return the target file path.

        Filenames and directory names are purely opaque/random and contain no user or template data.
        """
        clean_ext = file_format.strip().lower().lstrip(".")
        if clean_ext not in SUPPORTED_ARTIFACT_FORMATS:
            raise ValueError(
                f"Unsupported artifact file format {file_format!r}. Supported formats: {sorted(SUPPORTED_ARTIFACT_FORMATS)}"
            )

        if not prefix or not VALID_PREFIX_REGEX.match(prefix) or ".." in prefix or "/" in prefix or "\\" in prefix:
            raise ValueError(f"Invalid artifact prefix {prefix!r}. Must match regex {VALID_PREFIX_REGEX.pattern}")

        token = secrets.token_hex(16)
        art_dir = self._temp_root / f"{prefix}_{token}"
        art_dir.mkdir(parents=True, exist_ok=True)

        return art_dir / f"document.{clean_ext}"

    def cleanup_stale_artifacts(self, max_age_minutes: int | None = None) -> int:
        """Opportunistically purge temporary artifact directories/files older than TTL (default 10 minutes).

        Enforces strict path safety and component-aware containment: will never delete files outside temp_root.
        Symlinks pointing outside temp_root are unlinked directly without traversing.
        Returns the count of purged artifact directories/files.
        """
        if not self._temp_root.exists():
            return 0

        current_time = self._now()
        age_limit = timedelta(minutes=max_age_minutes if max_age_minutes is not None else self._ttl_minutes)
        cutoff_timestamp = (current_time - age_limit).timestamp()
        purged = 0

        # Safely inspect all immediate children without automatically following symlinks
        for child in list(self._temp_root.iterdir()):
            try:
                # Check if symlink: do not follow symlink to external target
                if child.is_symlink():
                    mtime = child.lstat().st_mtime
                    if mtime <= cutoff_timestamp:
                        child.unlink(missing_ok=True)
                        purged += 1
                    continue

                # Component-aware containment check
                resolved_child = child.resolve()
                if not resolved_child.is_relative_to(self._temp_root) or resolved_child == self._temp_root:
                    continue

                mtime = child.stat().st_mtime
                if mtime <= cutoff_timestamp:
                    if child.is_dir():
                        shutil.rmtree(child, ignore_errors=True)
                    else:
                        child.unlink(missing_ok=True)
                    purged += 1
            except OSError:
                pass

        return purged

    def cleanup_artifact(self, artifact_path: Path | str) -> bool:
        """Explicitly delete an artifact file and its enclosing dedicated temporary directory."""
        try:
            target = Path(artifact_path)

            if target.is_symlink():
                # If symlink is inside temp_root, unlink only the symlink itself
                if target.parent.resolve().is_relative_to(self._temp_root):
                    target.unlink(missing_ok=True)
                    return True
                return False

            resolved_target = target.resolve()
            # Component-aware containment check
            if not resolved_target.is_relative_to(self._temp_root) or resolved_target == self._temp_root:
                return False

            if resolved_target.is_file():
                parent = resolved_target.parent
                resolved_target.unlink(missing_ok=True)
                # If parent is a dedicated artifact directory inside temp_root, remove it
                if parent != self._temp_root and parent.is_relative_to(self._temp_root):
                    shutil.rmtree(parent, ignore_errors=True)
                return True
            elif resolved_target.is_dir() and resolved_target != self._temp_root:
                shutil.rmtree(resolved_target, ignore_errors=True)
                return True
        except OSError:
            pass

        return False

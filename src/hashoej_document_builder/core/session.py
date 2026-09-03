"""In-memory RAM session store for transient GenerationSession lifecycle."""

from __future__ import annotations

from collections.abc import Callable
import copy
from datetime import datetime, timedelta, timezone
import secrets
import threading
from typing import Any

from hashoej_document_builder.core.models import GenerationSession, utc_now

DEFAULT_INACTIVITY_TTL_MINUTES = 60


class SessionStore:
    """Thread-safe, RAM-only store for transient GenerationSessions with opportunistic cleanup."""

    def __init__(
        self,
        ttl_minutes: int = DEFAULT_INACTIVITY_TTL_MINUTES,
        now_fn: Callable[[], datetime] = utc_now,
    ) -> None:
        self._ttl = timedelta(minutes=ttl_minutes)
        self._now = now_fn
        self._sessions: dict[str, GenerationSession] = {}
        self._lock = threading.Lock()

    def _purge_expired_locked(self, current_time: datetime) -> int:
        """Purge all expired sessions while self._lock is held."""
        expired_ids = [
            sid
            for sid, s in self._sessions.items()
            if (current_time - s.last_activity_at) > self._ttl
        ]
        for sid in expired_ids:
            del self._sessions[sid]
        return len(expired_ids)

    def create(
        self,
        template_id: str,
        template_version: int,
        initial_values: dict[str, Any] | None = None,
        initial_step: int = 0,
    ) -> GenerationSession:
        """Create and store a new GenerationSession with a secure random ID."""
        session_id = secrets.token_urlsafe(32)
        current_time = self._now()

        session = GenerationSession(
            session_id=session_id,
            template_id=template_id,
            template_version=template_version,
            current_step=initial_step,
            values=copy.deepcopy(initial_values or {}),
            draft_values={},
            created_at=current_time,
            last_activity_at=current_time,
        )

        with self._lock:
            self._purge_expired_locked(current_time)
            self._sessions[session_id] = copy.deepcopy(session)

        return copy.deepcopy(session)

    def get(self, session_id: str, touch: bool = False) -> GenerationSession | None:
        """Retrieve a detached copy of a session by ID.

        If expired, the session is removed and None is returned.
        If touch is True and the session is active, its last_activity_at is updated.
        """
        current_time = self._now()
        with self._lock:
            self._purge_expired_locked(current_time)
            session = self._sessions.get(session_id)
            if session is None:
                return None

            if touch:
                session.last_activity_at = current_time

            return copy.deepcopy(session)

    def touch(self, session_id: str) -> bool:
        """Extend the activity timestamp of an active session.

        Returns True if the session was found and updated, False otherwise.
        """
        current_time = self._now()
        with self._lock:
            self._purge_expired_locked(current_time)
            session = self._sessions.get(session_id)
            if session is None:
                return False

            session.last_activity_at = current_time
            return True

    def save(self, session: GenerationSession, touch: bool = True) -> bool:
        """Save/update an existing active session in the store.

        Does not resurrect unknown, deleted, or expired sessions.
        Returns True if the session was successfully updated, False otherwise.
        """
        current_time = self._now()
        with self._lock:
            self._purge_expired_locked(current_time)
            existing = self._sessions.get(session.session_id)
            if existing is None:
                return False

            session_copy = copy.deepcopy(session)
            if touch:
                session_copy.last_activity_at = current_time

            self._sessions[session.session_id] = session_copy
            return True

    def delete(self, session_id: str) -> bool:
        """Explicitly delete a session from the store.

        Returns True if deleted, False if not found.
        """
        current_time = self._now()
        with self._lock:
            self._purge_expired_locked(current_time)
            return self._sessions.pop(session_id, None) is not None

    def cleanup_expired(self) -> int:
        """Purge all expired sessions. Returns count of purged sessions."""
        current_time = self._now()
        with self._lock:
            return self._purge_expired_locked(current_time)

    def count(self) -> int:
        """Return the count of all currently active sessions, purging expired sessions."""
        current_time = self._now()
        with self._lock:
            self._purge_expired_locked(current_time)
            return len(self._sessions)

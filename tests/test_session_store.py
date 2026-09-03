from datetime import datetime, timedelta, timezone
import pytest

from hashoej_document_builder.core.session import SessionStore


def test_session_creation_generates_opaque_random_id() -> None:
    store = SessionStore()
    session = store.create(
        template_id="hif-01-role",
        template_version=1,
        initial_values={"role_name": "Kasserer"},
        initial_step=0,
    )

    assert isinstance(session.session_id, str)
    assert len(session.session_id) >= 32
    assert session.template_id == "hif-01-role"
    assert session.template_version == 1
    assert session.values == {"role_name": "Kasserer"}
    assert session.current_step == 0
    assert session.created_at.tzinfo == timezone.utc
    assert session.last_activity_at.tzinfo == timezone.utc


def test_session_store_mutation_isolation() -> None:
    """Modifying a retrieved session object does NOT mutate stored state without explicit save."""
    store = SessionStore()
    session = store.create("hif-01-role", 1, {"k": "v1"})

    # Retrieve detached copy and mutate its values dict
    fetched = store.get(session.session_id)
    assert fetched is not None
    fetched.values["k"] = "mutated_outside"
    fetched.values["injected"] = "malicious"

    # Subsequent retrieval from store must still have original values
    fresh = store.get(session.session_id)
    assert fresh is not None
    assert fresh.values == {"k": "v1"}
    assert "injected" not in fresh.values

    # Explicit save commits changes
    fresh.values["k"] = "authorized_change"
    saved = store.save(fresh)
    assert saved is True

    updated = store.get(session.session_id)
    assert updated is not None
    assert updated.values == {"k": "authorized_change"}


def test_save_does_not_resurrect_deleted_or_unknown_sessions() -> None:
    store = SessionStore()
    session = store.create("hif-01-role", 1)

    # Delete session
    assert store.delete(session.session_id) is True

    # Attempting to save deleted session must return False and not resurrect it
    assert store.save(session) is False
    assert store.get(session.session_id) is None

    # Saving a completely fabricated session must also return False
    session.session_id = "fabricated_random_id_12345678901234567890"
    assert store.save(session) is False
    assert store.get(session.session_id) is None


def test_inactivity_ttl_and_clock_advancement() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    def clock():
        return now

    store = SessionStore(ttl_minutes=60, now_fn=clock)
    session = store.create("hif-01-role", 1)

    # 30 minutes later: still active
    now += timedelta(minutes=30)
    assert store.get(session.session_id) is not None

    # Touch extends the TTL
    assert store.touch(session.session_id) is True

    # 45 minutes after touch (75 min total from creation): still active because touch reset the timer
    now += timedelta(minutes=45)
    active_session = store.get(session.session_id)
    assert active_session is not None

    # 61 minutes after last touch without activity: expired
    now += timedelta(minutes=61)
    assert store.get(session.session_id) is None

    # Saving to expired session returns False
    assert store.save(session) is False
    assert store.count() == 0


def test_opportunistic_cleanup_during_normal_traffic() -> None:
    """Expired sessions are physically purged during subsequent normal store operations without explicit cleanup calls."""
    now = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)

    def clock():
        return now

    store = SessionStore(ttl_minutes=60, now_fn=clock)

    # 1. Create abandoned session A
    session_a = store.create("hif-01-role", 1)
    assert store.count() == 1

    # 2. Advance clock beyond 60-minute TTL (70 minutes later)
    now += timedelta(minutes=70)

    # 3. Do not call get(session_a.session_id) or explicit cleanup_expired().
    # 4. Perform normal store activity for session B
    session_b = store.create("hif-02-task", 1)

    # 5. Verify through public methods: total count is exactly 1 (only session B exists)
    assert store.count() == 1
    assert store.get(session_b.session_id) is not None

    # Explicit cleanup finds 0 additional expired sessions because session A was already purged
    assert store.cleanup_expired() == 0


def test_touch_on_non_existent_session() -> None:
    store = SessionStore()
    assert store.touch("non_existent_id") is False


def test_cleanup_expired_sessions() -> None:
    now = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)

    def clock():
        return now

    store = SessionStore(ttl_minutes=60, now_fn=clock)
    s1 = store.create("hif-01-role", 1)

    now += timedelta(minutes=30)
    s2 = store.create("hif-02-task", 1)

    # Now s1 is 70 min old (expired), s2 is 40 min old (active)
    now += timedelta(minutes=40)

    purged = store.cleanup_expired()
    assert purged == 1
    assert store.get(s1.session_id) is None
    assert store.get(s2.session_id) is not None

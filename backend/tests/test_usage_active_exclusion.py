"""Active-user metrics must exclude admin + demo accounts (PR #7 follow-up).

Originally the snapshot's active_today/cumulative_active and the
/dashboard/adoption live login_active/magic_link_active counted every row with
a timestamp — including the 7 seeded demo personas and operator/admin logins.
A live prod smoke test (2026-05-24) confirmed the inflation: logging in as the
Marcus demo persona bumped active_today to 2. `real_accounts` already excluded
these; the active metrics must match.

The project has no integration-DB harness (tests mock db.execute), so we pin
the exclusion at the SQL layer: the shared filter helpers must compile to WHERE
clauses that drop admin + demo rows. End-to-end correctness is verified
separately against prod by re-running the snapshot.
"""
from sqlalchemy import select, func
from sqlalchemy.dialects import postgresql

from app.models.user import User
from app.models.attendee import Attendee
from app.services.usage_snapshot import (
    _DEMO_SUFFIX,
    _active_user_filter,
    _active_attendee_filter,
)


def _sql(stmt) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).lower()


def test_active_user_filter_excludes_admin_and_demo():
    sql = _sql(select(func.count(User.id)).where(*_active_user_filter()))
    assert "is_admin" in sql, "admin accounts must be excluded from active users"
    assert _DEMO_SUFFIX.lower() in sql, "demo email suffix must be excluded"
    assert "lower(" in sql, "demo match must be case-insensitive"


def test_active_attendee_filter_excludes_demo_and_admin_linked():
    sql = _sql(select(func.count(Attendee.id)).where(*_active_attendee_filter()))
    assert _DEMO_SUFFIX.lower() in sql, "demo-persona attendees must be excluded"
    assert "is_admin" in sql, "admin-linked attendees must be excluded via subquery"


def test_filters_are_non_empty():
    assert len(_active_user_filter()) >= 2
    assert len(_active_attendee_filter()) >= 2

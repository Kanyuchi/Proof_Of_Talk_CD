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
    _account_linked_filter,
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
    assert len(_account_linked_filter()) >= 1


def test_account_linked_filter_requires_user_row():
    """`_account_linked_filter` must produce an EXISTS subquery against `users`
    so cumulative_active counts only attendees with a real account. Without
    this, magic-link opens from unregistered directory rows inflated active
    above total accounts (425 opens vs 391 accounts on 2026-05-29)."""
    sql = _sql(select(func.count(Attendee.id)).where(*_account_linked_filter()))
    assert "exists" in sql, "must use EXISTS subquery to require linked user"
    assert "users" in sql, "EXISTS must reference the users table"
    assert "attendee_id" in sql, "EXISTS must join users.attendee_id = attendees.id"
    assert "is_admin" in sql, "linked user must be non-admin"
    assert _DEMO_SUFFIX.lower() in sql, "linked user must be non-demo"


def test_active_attendee_filter_alone_does_not_require_user():
    """The base attendee filter must remain account-agnostic so the
    `magic_link_active` engagement stat keeps counting unregistered openers.
    Account-link enforcement lives in `_account_linked_filter` (added 2026-05-29
    after the 425-opens-vs-391-accounts inversion)."""
    sql = _sql(select(func.count(Attendee.id)).where(*_active_attendee_filter()))
    assert "exists" not in sql, (
        "base filter must not use EXISTS; account-link enforcement is _account_linked_filter's job"
    )

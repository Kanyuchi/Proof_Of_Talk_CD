from datetime import date, datetime

from app.models.user import User
from app.models.attendee import Attendee
from app.models.usage_daily import UsageDaily


def test_user_has_last_login_at_column():
    assert "last_login_at" in User.__table__.columns
    assert User.__table__.columns["last_login_at"].nullable is True


def test_attendee_has_last_seen_at_column():
    assert "last_seen_at" in Attendee.__table__.columns
    assert Attendee.__table__.columns["last_seen_at"].nullable is True


def test_usage_daily_columns_and_pk():
    cols = UsageDaily.__table__.columns
    assert set(c.name for c in cols) == {
        "day", "total_accounts", "real_accounts", "active_today", "cumulative_active",
    }
    assert UsageDaily.__table__.primary_key.columns.keys() == ["day"]


def test_usage_daily_instantiable():
    row = UsageDaily(
        day=date(2026, 5, 24),
        total_accounts=162, real_accounts=154, active_today=0, cumulative_active=0,
    )
    assert row.real_accounts == 154

    # the two timestamp columns accept a datetime
    u = User(email="x@y.z", hashed_password="h", full_name="X", last_login_at=datetime.utcnow())
    assert u.last_login_at is not None

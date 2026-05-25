"""attendees.last_interest_notified_at exists and is nullable (reciprocity throttle)."""

def test_attendee_has_last_interest_notified_at():
    from app.models.attendee import Attendee
    cols = Attendee.__table__.columns
    assert "last_interest_notified_at" in cols
    assert cols["last_interest_notified_at"].nullable is True

"""Tests for Pydantic schemas."""
import pytest
from uuid import uuid4
from datetime import datetime
from app.schemas.attendee import AttendeeCreate, AttendeeResponse, MatchStatusUpdate


class TestAttendeeCreate:
    def test_valid_creation(self):
        data = AttendeeCreate(
            name="Test User",
            email="test@example.com",
            company="TestCo",
            title="CEO",
            ticket_type="vip",
            interests=["blockchain", "DeFi"],
            goals="Find partners",
        )
        assert data.name == "Test User"
        assert data.ticket_type == "vip"

    def test_defaults(self):
        data = AttendeeCreate(
            name="Test", email="t@t.com", company="Co", title="Dev"
        )
        assert data.ticket_type == "delegate"
        assert data.interests == []
        assert data.goals is None

    def test_optional_urls(self):
        data = AttendeeCreate(
            name="Test",
            email="t@t.com",
            company="Co",
            title="Dev",
            linkedin_url="https://linkedin.com/in/test",
            twitter_handle="@test",
            company_website="https://test.com",
        )
        assert data.linkedin_url is not None


class TestMatchStatusUpdate:
    def test_valid_status(self):
        update = MatchStatusUpdate(status="accepted")
        assert update.status == "accepted"

    def test_declined_status(self):
        update = MatchStatusUpdate(status="declined")
        assert update.status == "declined"

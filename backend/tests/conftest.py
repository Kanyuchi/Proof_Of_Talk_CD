import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
from app.models.attendee import Attendee, TicketType


@pytest.fixture
def seed_profiles():
    """Load the 5 test profiles from seed data."""
    seed_file = Path(__file__).parent.parent / "data" / "seed_profiles.json"
    with open(seed_file) as f:
        return json.load(f)


@pytest.fixture
def sample_attendee():
    """Create a sample Attendee object (not persisted)."""
    return Attendee(
        name="Amara Okafor",
        email="amara.okafor@abudhabi-swf.example",
        company="Abu Dhabi Sovereign Wealth Fund",
        title="Director of Digital Assets",
        ticket_type=TicketType.VIP,
        interests=["tokenised real-world assets", "blockchain infrastructure"],
        goals="Deploy $200M into tokenised real-world assets and blockchain infrastructure.",
        enriched_profile={},
        intent_tags=[],
    )


@pytest.fixture
def all_attendees(seed_profiles):
    """Create Attendee objects for all 5 test profiles."""
    attendees = []
    for p in seed_profiles:
        attendees.append(
            Attendee(
                name=p["name"],
                email=p["email"],
                company=p["company"],
                title=p["title"],
                ticket_type=TicketType(p["ticket_type"]),
                interests=p["interests"],
                goals=p["goals"],
                enriched_profile={},
                intent_tags=[],
            )
        )
    return attendees

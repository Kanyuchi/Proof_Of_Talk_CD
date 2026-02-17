"""Seed the database with the 5 test profiles from the case study."""
import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import engine, async_session, Base
from app.models.attendee import Attendee, TicketType


async def seed():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Load seed data
    seed_file = Path(__file__).parent.parent / "data" / "seed_profiles.json"
    with open(seed_file) as f:
        profiles = json.load(f)

    async with async_session() as db:
        for profile in profiles:
            # Check if already exists
            result = await db.execute(
                select(Attendee).where(Attendee.email == profile["email"])
            )
            if result.scalar():
                print(f"  Skipping {profile['name']} (already exists)")
                continue

            attendee = Attendee(
                name=profile["name"],
                email=profile["email"],
                company=profile["company"],
                title=profile["title"],
                ticket_type=TicketType(profile["ticket_type"]),
                interests=profile["interests"],
                goals=profile["goals"],
                linkedin_url=profile.get("linkedin_url"),
                twitter_handle=profile.get("twitter_handle"),
                company_website=profile.get("company_website"),
            )
            db.add(attendee)
            print(f"  Added {profile['name']} ({profile['title']}, {profile['company']})")

        await db.commit()
        print(f"\nSeeded {len(profiles)} test profiles.")


if __name__ == "__main__":
    print("Seeding database with test profiles...")
    asyncio.run(seed())

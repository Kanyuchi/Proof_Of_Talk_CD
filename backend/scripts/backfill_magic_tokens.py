"""Backfill magic_access_token for every attendee that doesn't have one.

The welcome email's "Open your matches" button links to /m/{magic_token}.
Attendees without a token fall back to the login wall (they bought a Rhuna
ticket and never set a password), so this must run before any welcome blast.

Mirrors the POST /matches/generate-tokens admin endpoint, but runnable from
the CLI with no auth juggling. Idempotent — only fills NULLs.

    python scripts/backfill_magic_tokens.py
"""
import asyncio
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.models.attendee import Attendee  # noqa: E402


async def main() -> None:
    async with async_session() as db:
        result = await db.execute(
            select(Attendee).where(Attendee.magic_access_token.is_(None))
        )
        attendees = result.scalars().all()
        for att in attendees:
            att.magic_access_token = secrets.token_urlsafe(32)
        await db.commit()
        print(f"Backfilled magic tokens for {len(attendees)} attendees.")


if __name__ == "__main__":
    asyncio.run(main())

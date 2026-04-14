"""Regenerate all matches — runs the full pipeline with the latest ranking logic."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session
from app.services.matching import run_matching_pipeline


async def main():
    async with async_session() as db:
        total = await run_matching_pipeline(db, top_k=10)
        print(f"Generated {total} matches")


if __name__ == "__main__":
    asyncio.run(main())

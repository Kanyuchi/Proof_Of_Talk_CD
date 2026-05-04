"""
Async wrapper around scripts/ingest_speakers_sheet.py
=====================================================
Lets the FastAPI scheduler and dashboard endpoint call the same ingest path
that ops runs from the CLI. The script does sync I/O (httpx.Client +
Supabase REST), so we offload to a worker thread.

Replaces the old speakers_sync.py path which read from the near-empty
Supabase `speakers` table managed by 1000 Minds. The Google Sheet
maintained by PoT ops is now the source of truth.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# scripts/ lives a sibling of app/ — add to import path
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _BACKEND_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


async def sync_speakers_sheet(fetch: bool = True) -> dict:
    """
    Run the speaker-sheet ingest. Pulls a fresh CSV snapshot from Google
    Sheets when `fetch=True` (the default — used by the daily cron).

    Returns the script's stats dict: total / inserted / patched / noop /
    errors / new_ids.
    """
    # Import lazily so that import-time failures in the script don't break
    # the FastAPI app boot.
    from ingest_speakers_sheet import DEFAULT_CSV, run

    def _go() -> dict:
        return run(csv_path=DEFAULT_CSV, fetch=fetch, dry_run=False)

    stats = await asyncio.to_thread(_go)
    logger.info("speakers_sheet_sync: complete", extra={"stats": stats})
    return stats

"""
Async wrapper around scripts/enrich_and_embed.py for the daily cron.

Reuses the script's run() function so the cron and the manual CLI
share identical enrichment logic — no drift between them. Skip LinkedIn
in the cron because that path needs a browser session + manual login.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _BACKEND_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


async def daily_enrichment_sweep() -> dict:
    """Run website + Grid + AI summary + embedding for any attendee whose
    enrichment is incomplete. Idempotent — already-enriched fields are
    skipped (see process_attendee's `_cached` branches)."""
    from enrich_and_embed import run

    stats = await run(dry_run=False, force=False, scrape_only=False, skip_linkedin=True)
    logger.info("enrichment_sweep: complete", extra={"stats": stats})
    return stats or {}

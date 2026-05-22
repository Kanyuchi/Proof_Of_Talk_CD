#!/usr/bin/env python3
"""Seed 7 isolated demo personas for video recording in the matchmaking app.

Full Web3 profiles (title, company, goals, interests, target_companies,
socials, AI summary, vertical/intent tags) + real OpenAI embeddings +
AI-generated face photos uploaded to the `avatars` bucket + login accounts +
a curated match graph AMONG THEMSELVES (fresh / mutual / booked-meeting states).

ISOLATION: every persona is on @demo.proofoftalk.io, which is in
staff_filter.INTERNAL_EMAIL_DOMAINS — so they never appear in real attendees'
candidate retrieval (both directions) and are excluded from dashboard counts.
Because they already have matches, the daily refresh skips them.

Idempotent: re-running upserts the profiles, re-uploads photos, and rebuilds
the demo match graph. Safe to run repeatedly.

CAVEAT: a manual full `generate_all_matches` wipes ALL matches incl. these.
Re-run this script (or `--matches-only`) afterward to restore the demo graph.

Usage:
    python scripts/seed_demo_profiles.py                # full seed
    python scripts/seed_demo_profiles.py --matches-only # rebuild just the match graph
    python scripts/seed_demo_profiles.py --skip-photos  # skip photo fetch/upload
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from sqlalchemy import select, or_, and_, delete  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.attendee import Attendee, Match  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.embeddings import embed_attendee  # noqa: E402
from app.services import avatars  # noqa: E402
import secrets  # noqa: E402

DEMO_DOMAIN = "demo.proofoftalk.io"
DEMO_PASSWORD = "ProofDemo2026!"
FACE_URL = "https://thispersondoesnotexist.com/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# --- the 7 personas (order matters: indices referenced by MATCHES below) -------
PERSONAS = [
    dict(
        key="amara", name="Amara Okafor", title="General Partner",
        company="Lattice Capital", email=f"amara@{DEMO_DOMAIN}",
        twitter_handle="amaraokafor", linkedin_url="https://www.linkedin.com/in/amara-okafor-demo",
        goals="Deploying our $120M fund into pre-seed and seed Web3 infrastructure and DeFi. Looking for technical founders solving real on-chain problems, especially in privacy, modular L2s, and institutional rails.",
        target_companies="ZK / privacy founders, modular rollup teams, institutional DeFi, anyone building compliant on-chain infrastructure",
        interests=["DeFi", "ZK / privacy", "modular L2s", "institutional crypto", "fund strategy"],
        vertical_tags=["DeFi", "Infrastructure"], intent_tags=["deploying_capital", "deal_making"],
        ai_summary="Amara is a General Partner at Lattice Capital deploying a $120M fund into pre-seed and seed Web3 infrastructure and DeFi. She is most interested in technical founders in privacy, modular L2s, and institutional rails, and is actively writing first cheques at Proof of Talk.",
    ),
    dict(
        key="marcus", name="Marcus Chen", title="Co-Founder & CEO",
        company="Veil", email=f"marcus@{DEMO_DOMAIN}",
        twitter_handle="marcuschen", linkedin_url="https://www.linkedin.com/in/marcus-chen-demo",
        goals="Raising a $6M seed for Veil, a ZK privacy layer for compliant institutional transactions. Looking for thesis-aligned investors and exchange / custody partners to bring privacy-preserving settlement to regulated desks.",
        target_companies="infra-focused VCs, exchanges and custodians, compliance-forward funds, L2 ecosystems",
        interests=["ZK / privacy", "institutional settlement", "compliance tech", "fundraising"],
        vertical_tags=["Infrastructure", "Privacy"], intent_tags=["raising_capital", "finding_partners"],
        ai_summary="Marcus is co-founder and CEO of Veil, a ZK privacy layer for compliant institutional transactions, raising a $6M seed. He is looking for thesis-aligned infra investors and exchange/custody partners to bring privacy-preserving settlement to regulated desks.",
    ),
    dict(
        key="sofia", name="Sofia Reyes", title="Head of Policy",
        company="Aegis Compliance", email=f"sofia@{DEMO_DOMAIN}",
        twitter_handle="sofiareyes", linkedin_url="https://www.linkedin.com/in/sofia-reyes-demo",
        goals="Shaping practical MiCA and travel-rule guidance that builders can actually ship against. Looking to meet infrastructure and exchange teams to pressure-test upcoming rules and co-author implementation playbooks.",
        target_companies="L2 / infra builders, exchanges, custodians, stablecoin issuers",
        interests=["regulation", "MiCA", "travel rule", "stablecoins", "compliance"],
        vertical_tags=["Regulation", "Compliance"], intent_tags=["policy_shaping", "finding_partners"],
        ai_summary="Sofia leads policy at Aegis Compliance, focused on practical MiCA and travel-rule guidance. She wants to meet infrastructure and exchange teams to pressure-test upcoming rules and co-author implementation playbooks.",
    ),
    dict(
        key="daniel", name="Daniel Kim", title="Co-Founder",
        company="Orbit Rollups", email=f"daniel@{DEMO_DOMAIN}",
        twitter_handle="danielkim", linkedin_url="https://www.linkedin.com/in/daniel-kim-demo",
        goals="Scaling Orbit, a modular L2 rollup stack. Looking for ecosystem partners, app teams to deploy on Orbit, and regulatory clarity on data availability and sequencer decentralisation.",
        target_companies="app-chain teams, DeFi protocols, regulators, infra VCs, DevRel / ecosystem leads",
        interests=["modular L2s", "rollups", "data availability", "ecosystem growth"],
        vertical_tags=["Infrastructure"], intent_tags=["finding_partners", "ecosystem_growth"],
        ai_summary="Daniel co-founded Orbit Rollups, a modular L2 rollup stack. He is seeking app teams to deploy on Orbit, ecosystem partners, and regulatory clarity on data availability and sequencer decentralisation.",
    ),
    dict(
        key="priya", name="Priya Nair", title="Global Head of Business Development",
        company="Meridian Exchange", email=f"priya@{DEMO_DOMAIN}",
        twitter_handle="priyanair", linkedin_url="https://www.linkedin.com/in/priya-nair-demo",
        goals="Sourcing high-quality projects for listing and growing Meridian's institutional custody book. Looking for founders ready to list and asset managers who need regulated custody and execution.",
        target_companies="token projects ready to list, institutional asset managers, custody buyers",
        interests=["exchange listings", "institutional custody", "market making", "BD"],
        vertical_tags=["Exchange", "Custody"], intent_tags=["deal_making", "finding_partners"],
        ai_summary="Priya runs global BD at Meridian Exchange, sourcing projects for listing and growing the institutional custody book. She wants to meet founders ready to list and asset managers needing regulated custody and execution.",
    ),
    dict(
        key="thomas", name="Thomas Weber", title="Head of Digital Assets",
        company="Hanseatic Asset Management", email=f"thomas@{DEMO_DOMAIN}",
        twitter_handle="thomasweber", linkedin_url="https://www.linkedin.com/in/thomas-weber-demo",
        goals="Bringing a $40B traditional asset manager on-chain. Looking for compliant custody, regulated execution venues, and tokenisation infrastructure we can take to our investment committee this year.",
        target_companies="custodians, regulated exchanges, tokenisation platforms, compliance advisors",
        interests=["tokenisation", "institutional custody", "RWAs", "compliance", "TradFi"],
        vertical_tags=["Institutional", "RWA"], intent_tags=["deploying_capital", "finding_partners"],
        ai_summary="Thomas leads digital assets at Hanseatic Asset Management, a $40B traditional manager moving on-chain. He is looking for compliant custody, regulated execution venues, and tokenisation infrastructure ready for an investment committee.",
    ),
    dict(
        key="lena", name="Lena Volkov", title="Ecosystem Lead",
        company="Spark DAO", email=f"lena@{DEMO_DOMAIN}",
        twitter_handle="lenavolkov", linkedin_url="https://www.linkedin.com/in/lena-volkov-demo",
        goals="Growing the Spark builder ecosystem with grants, hackathons, and integrations. Looking for infrastructure teams to integrate, founders to support, and event / community partners.",
        target_companies="L2 / infra teams, early founders, DevRel leads, event organisers",
        interests=["DevRel", "grants", "community", "hackathons", "ecosystem growth"],
        vertical_tags=["Community", "Infrastructure"], intent_tags=["ecosystem_growth", "finding_partners"],
        ai_summary="Lena is ecosystem lead at Spark DAO, growing the builder ecosystem through grants, hackathons, and integrations. She wants to meet infrastructure teams to integrate, founders to support, and event/community partners.",
    ),
]

# --- curated match graph (by persona key) --------------------------------------
# state: "fresh" (both pending), "mutual" (both accepted), "meeting" (mutual + booked)
MATCHES = [
    dict(a="amara", b="marcus", type="deal_ready", score=0.92, state="meeting",
         why="Amara's fund thesis (privacy + institutional rails) is a near-perfect fit for Veil's ZK settlement layer, and Marcus is actively raising the exact round she writes. A clear first-cheque conversation — both are deal-ready."),
    dict(a="priya", b="marcus", type="complementary", score=0.84, state="mutual",
         why="Meridian wants compliant, privacy-preserving projects to list; Veil needs an exchange/custody partner to reach regulated desks. Listing + settlement integration is the obvious next step."),
    dict(a="thomas", b="priya", type="deal_ready", score=0.88, state="fresh",
         why="Thomas needs regulated custody and execution to bring Hanseatic on-chain; Priya is growing exactly that institutional custody book. A direct buyer–provider match with budget on the table."),
    dict(a="sofia", b="daniel", type="complementary", score=0.81, state="fresh",
         why="Sofia is drafting rules Daniel has to build against; Daniel can show her what data-availability and sequencer decentralisation actually require. Co-authoring an implementation playbook helps both sides."),
    dict(a="amara", b="daniel", type="deal_ready", score=0.86, state="fresh",
         why="Orbit's modular L2 stack sits squarely in Lattice's infrastructure thesis. Amara backs infra at this stage and Daniel is scaling — a strong investor–founder fit."),
    dict(a="marcus", b="daniel", type="non_obvious", score=0.77, state="fresh",
         why="Two infra founders solving adjacent problems: Veil's privacy layer could deploy natively on Orbit's rollup stack, turning a peer chat into a technical integration."),
    dict(a="sofia", b="thomas", type="complementary", score=0.79, state="fresh",
         why="Thomas needs a defensible compliance story for his investment committee; Sofia shapes the very MiCA guidance he'll be judged against. High-signal for both."),
    dict(a="lena", b="daniel", type="complementary", score=0.74, state="fresh",
         why="Spark's grants and hackathons can seed an app ecosystem on Orbit. A natural ecosystem-growth partnership between a DAO ecosystem lead and an L2 founder."),
    dict(a="lena", b="marcus", type="complementary", score=0.72, state="fresh",
         why="Lena supports early founders with grants and community; Marcus could use ecosystem distribution for Veil. A useful supporter-to-founder connection."),
    dict(a="thomas", b="amara", type="non_obvious", score=0.71, state="fresh",
         why="A TradFi asset manager and a crypto-native GP rarely share a thesis, yet both want compliant institutional rails — a non-obvious co-investment and knowledge-exchange opportunity."),
]


async def _fetch_face(client: httpx.AsyncClient) -> bytes | None:
    try:
        r = await client.get(FACE_URL, headers={"User-Agent": UA}, timeout=30, follow_redirects=True)
        if r.status_code == 200 and r.content and len(r.content) > 5000:
            return r.content
        print(f"    face fetch unexpected: {r.status_code}, {len(r.content)} bytes")
    except Exception as e:  # noqa: BLE001
        print(f"    face fetch error: {type(e).__name__}: {e}")
    return None


async def upsert_personas(db, skip_photos: bool) -> dict:
    """Create/update the 7 attendee rows + login accounts + photos + embeddings.
    Returns {key: attendee} map."""
    by_key = {}
    async with httpx.AsyncClient() as client:
        for p in PERSONAS:
            existing = (await db.execute(
                select(Attendee).where(Attendee.email == p["email"])
            )).scalars().first()
            att = existing or Attendee()
            att.name = p["name"]; att.email = p["email"]; att.company = p["company"]
            att.title = p["title"]; att.goals = p["goals"]; att.target_companies = p["target_companies"]
            att.interests = p["interests"]; att.twitter_handle = p["twitter_handle"]
            att.linkedin_url = p["linkedin_url"]; att.ai_summary = p["ai_summary"]
            att.vertical_tags = p["vertical_tags"]; att.intent_tags = p["intent_tags"]
            att.ticket_type = "DELEGATE"; att.privacy_mode = "full"
            att.matching_consent = "not_required"; att.email_opt_out = False
            if not att.magic_access_token:
                att.magic_access_token = secrets.token_urlsafe(32)
            if not existing:
                db.add(att)
            await db.flush()  # assign id

            # Embedding from the composite profile text.
            try:
                att.embedding = await embed_attendee(att)
            except Exception as e:  # noqa: BLE001
                print(f"  {p['name']}: embedding failed: {e}")

            # Photo: AI face → avatars bucket.
            if not skip_photos:
                face = await _fetch_face(client)
                if face:
                    try:
                        url = await avatars.upload_avatar(str(att.id), face, "image/jpeg")
                        att.photo_url = url
                        print(f"  {p['name']}: photo ok")
                    except Exception as e:  # noqa: BLE001
                        print(f"  {p['name']}: photo upload failed: {e}")
                else:
                    print(f"  {p['name']}: no photo (fetch failed) — initials fallback")

            # Login account (shared demo password).
            user = (await db.execute(
                select(User).where(User.email == p["email"])
            )).scalars().first()
            if not user:
                user = User(email=p["email"], full_name=p["name"],
                            hashed_password=get_password_hash(DEMO_PASSWORD),
                            is_admin=False, attendee_id=att.id)
                db.add(user)
            else:
                user.hashed_password = get_password_hash(DEMO_PASSWORD)
                user.attendee_id = att.id
            by_key[p["key"]] = att
            print(f"  {p['name']} <{p['email']}> ready (id={att.id})")
    await db.commit()
    return by_key


async def rebuild_matches(db, by_key: dict) -> int:
    """Delete + recreate the curated match graph among the demo personas only."""
    ids = [a.id for a in by_key.values()]
    await db.execute(
        delete(Match).where(
            and_(Match.attendee_a_id.in_(ids), Match.attendee_b_id.in_(ids))
        )
    )
    await db.commit()

    from datetime import datetime
    n = 0
    for m in MATCHES:
        a = by_key[m["a"]]; b = by_key[m["b"]]
        state = m["state"]
        sa = sb = "pending"; status = "pending"; meeting_time = None
        if state in ("mutual", "meeting"):
            sa = sb = "accepted"; status = "accepted"
        if state == "meeting":
            # June 2 2026, 10:30 — a real conference slot
            meeting_time = datetime(2026, 6, 2, 10, 30)
        row = Match(
            attendee_a_id=a.id, attendee_b_id=b.id,
            similarity_score=m["score"], complementary_score=m["score"],
            overall_score=m["score"], match_type=m["type"], explanation=m["why"],
            shared_context={"sectors": list({*a.vertical_tags, *b.vertical_tags})},
            status=status, status_a=sa, status_b=sb, meeting_time=meeting_time,
            tier="curated",
        )
        db.add(row)
        n += 1
    await db.commit()
    return n


async def main(matches_only: bool, skip_photos: bool):
    async with async_session() as db:
        if matches_only:
            by_key = {}
            for p in PERSONAS:
                att = (await db.execute(
                    select(Attendee).where(Attendee.email == p["email"])
                )).scalars().first()
                if not att:
                    print(f"  ERROR: {p['email']} not found — run full seed first")
                    return
                by_key[p["key"]] = att
        else:
            print("Upserting 7 demo personas…")
            by_key = await upsert_personas(db, skip_photos)
        print("Rebuilding curated match graph…")
        count = await rebuild_matches(db, by_key)
        print(f"\nDone: {len(by_key)} personas, {count} demo matches.")
        print(f"Login: any persona email @ {DEMO_DOMAIN}  /  password: {DEMO_PASSWORD}")
        print("Magic links:")
        for p in PERSONAS:
            att = by_key.get(p["key"])
            if att and att.magic_access_token:
                print(f"  {p['name']}: https://meet.proofoftalk.io/m/{att.magic_access_token}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches-only", action="store_true", help="Rebuild just the match graph")
    ap.add_argument("--skip-photos", action="store_true", help="Skip photo fetch/upload")
    args = ap.parse_args()
    asyncio.run(main(args.matches_only, args.skip_photos))

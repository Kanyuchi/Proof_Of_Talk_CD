"""Stage the demo data for the REAL-APP onboarding screen recording.

Produces ONE coherent, demo-safe identity — "Alex Rivera"
(alex.video@demo.proofoftalk.io) — that the Playwright recorder drives through
the real flow: magic-link claim -> set password -> profile/write-up -> matches
-> accept -> mutual messages -> booking -> threads.

Everything is @demo.proofoftalk.io, so it is excluded from every adoption /
usage metric (see dashboard.py, usage_snapshot.py, interest_cron.py) and the
concierge candidate scope keeps demo viewers seeing ONLY other demo personas.

What it does (idempotent — safe to re-run):
  1. Upserts the Alex Rivera attendee (DELEGATE, privacy=full, goals+interests,
     a magic_access_token). Casts him as a tokenisation/RWA-infra founder so he
     complements the 7 existing demo personas (asset manager, exchange BD,
     infra investor, policy lead, L2 founders).
  2. DELETES any `users` row linked to Alex so the claim / set-password flow
     works on camera (the recorder will create the account live).
  3. Embeds Alex (real OpenAI embedding via process_attendee) so he is a real
     vector in pgvector — then REPLACES his match rows with hand-built curated
     matches to the demo personas ONLY (guarantees no real attendee name ever
     appears on camera). One match is set MUTUAL so it lands in Messages with
     the composer enabled + free-slot chips.
  4. Seeds a couple of thread posts from demo personas so /threads is not empty.

Run:
    cd backend && source .venv/bin/activate
    python scripts/stage_onboarding_video_demo.py            # stage
    python scripts/stage_onboarding_video_demo.py --reset    # delete Alex's
                                                             # user row only
                                                             # (re-arm the claim)
"""
import argparse
import asyncio
import secrets
import sys
import uuid
from datetime import datetime

from sqlalchemy import select, delete, or_

# Allow `python scripts/...` from the backend dir.
sys.path.insert(0, ".")

from app.core.database import async_session  # noqa: E402
from app.models.attendee import Attendee, Match, TicketType  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.message import Thread, ThreadPost, Conversation, Message  # noqa: E402
from app.services.matching import MatchingEngine  # noqa: E402

ALEX_EMAIL = "alex.video@demo.proofoftalk.io"
ALEX_NAME = "Alex Rivera"

ALEX_FIELDS = dict(
    name=ALEX_NAME,
    company="Meridian RWA",
    title="Founder & CEO",
    ticket_type=TicketType.DELEGATE,
    privacy_mode="full",
    goals=(
        "Raising a $5M seed for Meridian RWA — onchain tokenisation rails for "
        "regulated real-world assets (private credit, T-bills). Looking for "
        "thesis-aligned infra investors, a regulated custody / execution "
        "partner, and an asset manager design partner to take a first product "
        "to their investment committee."
    ),
    interests=[
        "tokenisation",
        "RWAs",
        "institutional custody",
        "compliance",
        "fundraising",
    ],
    vertical_tags=["RWA", "Infrastructure"],
    intent_tags=["raising_capital", "seeking_partnerships", "finding_partners"],
    deal_readiness_score=0.82,
    linkedin_url="https://www.linkedin.com/in/alexrivera-rwa",
    twitter_handle="alexrwa",
    company_website="https://meridian-rwa.xyz",
)

# Hand-built curated matches Alex -> demo personas. Keys are demo emails so we
# never hardcode UUIDs. (overall, similarity, complementary, type, explanation,
# shared_sectors, action_items). Ordered best-first; the FIRST one is set mutual.
DEMO_MATCHES = [
    (
        "thomas@demo.proofoftalk.io",
        0.89, 0.83, 0.92, "deal_ready",
        "Thomas is bringing a $40B asset manager on-chain and needs tokenisation "
        "infrastructure he can take to his investment committee; Alex is building "
        "exactly that for regulated RWAs. A direct design-partner fit with budget "
        "in reach.",
        ["RWA", "Tokenisation", "Institutional", "Compliance"],
        [
            "Scope a first tokenised private-credit product for Hanseatic's IC",
            "Map the custody + execution stack each side already trusts",
        ],
    ),
    (
        "priya@demo.proofoftalk.io",
        0.84, 0.80, 0.86, "complementary",
        "Priya is growing Meridian Exchange's institutional custody book and "
        "sources listable projects; Alex needs regulated custody and a venue for "
        "tokenised assets. Buyer-provider on custody, plus a listing path.",
        ["Custody", "Exchange", "RWA", "Institutional"],
        [
            "Pressure-test custody requirements for tokenised T-bills",
            "Explore a listing / distribution path for Meridian RWA assets",
        ],
    ),
    (
        "amara@demo.proofoftalk.io",
        0.81, 0.84, 0.79, "complementary",
        "RWA tokenisation rails sit squarely in Lattice's infra + DeFi thesis, "
        "and Alex is raising a seed at exactly the stage Amara deploys. A clean "
        "investor-founder fit on the $5M round.",
        ["RWA", "Infrastructure", "DeFi"],
        [
            "Walk Amara through the seed deck + traction",
            "Test the thesis fit: regulated RWA infra at pre-seed/seed",
        ],
    ),
    (
        "sofia@demo.proofoftalk.io",
        0.76, 0.71, 0.80, "non_obvious",
        "Sofia shapes the MiCA / travel-rule guidance Alex has to ship against; "
        "Alex gives her a live builder to pressure-test upcoming RWA rules. "
        "High-signal for both, even though neither is selling to the other.",
        ["Regulation", "Compliance", "RWA"],
        [
            "Pressure-test draft RWA tokenisation guidance against a real product",
            "Co-author an implementation note builders can actually follow",
        ],
    ),
]


async def _get_demo(db, email):
    return (await db.execute(select(Attendee).where(Attendee.email == email))).scalars().first()


async def build_demo_matches(db, alex):
    """Delete Alex's match rows and rebuild the hand-built demo-only curated set.

    Returns the mutual match id. Idempotent — used both at first stage and to
    RE-STAGE matches after a profile save (the real app's `refresh_profile_matches`
    fires on every save and would otherwise replace these with real-pool matches,
    putting real attendees on camera and clearing the mutual Thomas thread).
    """
    await db.execute(
        delete(Match).where(or_(Match.attendee_a_id == alex.id, Match.attendee_b_id == alex.id))
    )
    await db.commit()

    mutual_match_id = None
    for i, (email, overall, sim, comp, mtype, expl, sectors, actions) in enumerate(DEMO_MATCHES):
        other = await _get_demo(db, email)
        if not other:
            print(f"[stage] WARN demo persona {email} missing — skipping")
            continue
        is_mutual = i == 0
        m = Match(
            id=uuid.uuid4(),
            attendee_a_id=alex.id,
            attendee_b_id=other.id,
            similarity_score=sim,
            complementary_score=comp,
            overall_score=overall,
            match_type=mtype,
            explanation=expl,
            shared_context={"sectors": sectors, "action_items": actions},
            tier="curated",
            status="accepted" if is_mutual else "pending",
            status_a="accepted" if is_mutual else "pending",
            status_b="accepted" if is_mutual else "pending",
        )
        db.add(m)
        if is_mutual:
            mutual_match_id = m.id
        tag = "MUTUAL" if is_mutual else "pending"
        print(f"[stage]   match Alex <-> {other.name:13} {mtype:13} {overall:.2f} [{tag}]")
    await db.commit()
    return mutual_match_id


async def restage_matches_only(db):
    """Re-arm just the demo matches (after the on-camera profile save wiped them)."""
    alex = await _get_demo(db, ALEX_EMAIL)
    if not alex:
        print(f"[matches-only] no Alex attendee — run full stage first")
        return
    if alex.embedding is None:
        engine = MatchingEngine(db)
        await engine.process_attendee(alex)
        await db.commit()
        await db.refresh(alex)
    mutual = await build_demo_matches(db, alex)
    print(f"[matches-only] rebuilt demo matches; mutual={mutual}")
    print(f"MUTUAL_MATCH_ID={mutual}")


async def reset_user_only(db):
    """Delete Alex's users row (if any) so the claim/set-password flow re-arms."""
    alex = await _get_demo(db, ALEX_EMAIL)
    if not alex:
        print(f"[reset] no Alex attendee yet ({ALEX_EMAIL}) — nothing to reset")
        return
    res = await db.execute(delete(User).where(User.attendee_id == alex.id))
    await db.execute(delete(User).where(User.email == ALEX_EMAIL))
    await db.commit()
    print(f"[reset] deleted {res.rowcount} user row(s) for Alex ({alex.id}) — claim flow re-armed")


async def stage(db):
    # 1. Upsert Alex --------------------------------------------------------
    alex = await _get_demo(db, ALEX_EMAIL)
    if alex:
        print(f"[stage] Alex exists ({alex.id}) — refreshing fields")
        for k, v in ALEX_FIELDS.items():
            setattr(alex, k, v)
        if not alex.magic_access_token:
            alex.magic_access_token = secrets.token_urlsafe(32)
    else:
        alex = Attendee(
            id=uuid.uuid4(),
            email=ALEX_EMAIL,
            magic_access_token=secrets.token_urlsafe(32),
            **ALEX_FIELDS,
        )
        db.add(alex)
        print(f"[stage] created Alex ({alex.id})")
    # Clear any prior embedding so process_attendee regenerates a fresh one.
    alex.embedding = None
    await db.commit()
    await db.refresh(alex)

    # 2. Delete Alex's users row so the claim flow works on camera ----------
    res = await db.execute(delete(User).where(or_(User.attendee_id == alex.id, User.email == ALEX_EMAIL)))
    if res.rowcount:
        print(f"[stage] deleted {res.rowcount} pre-existing user row(s) for Alex (claim flow armed)")
    await db.commit()

    # 3. Embed Alex (REAL embedding) ---------------------------------------
    engine = MatchingEngine(db)
    await engine.process_attendee(alex)
    await db.commit()
    await db.refresh(alex)
    print(f"[stage] embedded Alex: embedding={'set' if alex.embedding is not None else 'MISSING'}")

    # Replace Alex's match rows with the hand-built demo-only curated set so
    # no real attendee can surface on camera.
    mutual_match_id = await build_demo_matches(db, alex)

    # 4. Seed a couple of thread posts so /threads is not empty -------------
    #    (the threads route auto-creates the 11 default threads on first GET,
    #     but we add demo posts so the thread Alex opens has content.)
    await seed_thread_posts(db)

    # Re-fetch token (refresh expired it).
    await db.refresh(alex)
    return alex, mutual_match_id


DEMO_THREAD_SLUG = "rwa_tokenisation_demo"
DEMO_THREAD_TITLE = "Tokenisation & RWA — Builders Circle"
DEMO_THREAD_DESC = "Real-world assets, security tokens, and the future of tokenised finance."


async def seed_thread_posts(db):
    """Seed a DEMO-ONLY thread with demo-persona posts.

    We use a dedicated demo thread (not the shared default "tokenisation_of_finance"
    thread) so NO real attendee's post appears on camera — the public default
    threads mix real and demo authors, which we don't want in a marketing clip.
    The recorder opens this thread (title "Tokenisation & RWA") for the threads
    beat. The 11 public default threads still exist and are untouched.
    """
    # Make sure default threads exist too (so the threads LIST looks populated).
    from app.api.routes.threads import _ensure_default_threads
    await _ensure_default_threads(db)

    thread = (await db.execute(
        select(Thread).where(Thread.slug == DEMO_THREAD_SLUG)
    )).scalars().first()
    if not thread:
        thread = Thread(
            id=uuid.uuid4(),
            slug=DEMO_THREAD_SLUG,
            title=DEMO_THREAD_TITLE,
            description=DEMO_THREAD_DESC,
        )
        db.add(thread)
        await db.commit()
        await db.refresh(thread)
        print(f"[stage] created demo-only thread '{thread.title}' ({DEMO_THREAD_SLUG})")

    existing = (await db.execute(
        select(ThreadPost).where(ThreadPost.thread_id == thread.id)
    )).scalars().all()
    if len(existing) >= 2:
        print(f"[stage] demo thread '{thread.title}' already has {len(existing)} post(s) — skipping seed")
        return

    seed = [
        ("thomas@demo.proofoftalk.io",
         "We're evaluating tokenised private credit for a first onchain product. "
         "Biggest open question for us is custody + transfer-agent integration — "
         "who's solved this for a regulated book?"),
        ("sofia@demo.proofoftalk.io",
         "On the regulatory side: the travel-rule and MiCA reporting hooks are "
         "where most RWA designs break. Happy to share a checklist if anyone's "
         "shipping this year."),
        ("priya@demo.proofoftalk.io",
         "From the exchange side we're seeing real institutional demand for "
         "tokenised T-bills — listing + distribution is the easy part now, "
         "custody is the bottleneck."),
    ]
    added = 0
    for email, content in seed:
        a = await _get_demo(db, email)
        if not a:
            continue
        db.add(ThreadPost(
            id=uuid.uuid4(),
            thread_id=thread.id,
            sender_attendee_id=a.id,
            content=content,
            created_at=datetime.utcnow(),
        ))
        added += 1
    await db.commit()
    print(f"[stage] seeded {added} post(s) into thread '{thread.title}'")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true",
                    help="Only delete Alex's user row (re-arm the claim flow), no re-stage")
    ap.add_argument("--matches-only", action="store_true",
                    help="Only rebuild Alex's demo matches (after an on-camera profile "
                         "save wiped them via refresh_profile_matches)")
    args = ap.parse_args()

    async with async_session() as db:
        if args.reset:
            await reset_user_only(db)
            return
        if args.matches_only:
            await restage_matches_only(db)
            return
        alex, mutual_id = await stage(db)

    print("\n================ STAGING SUMMARY ================")
    print(f"Alex attendee id : {alex.id}")
    print(f"Alex email       : {ALEX_EMAIL}")
    print(f"Magic token      : {alex.magic_access_token}")
    print(f"Magic-link URL   : http://localhost:5173/m/{alex.magic_access_token}?unlock=1")
    print(f"Mutual match id  : {mutual_id} (Alex <-> Thomas Weber, set accepted/accepted)")
    print("Password to set  : Paris2026! (recorder uses this)")
    print("================================================")
    # Emit a machine-readable line the recorder can grep.
    print(f"MAGIC_TOKEN={alex.magic_access_token}")
    print(f"ALEX_ID={alex.id}")
    print(f"MUTUAL_MATCH_ID={mutual_id}")


if __name__ == "__main__":
    asyncio.run(main())

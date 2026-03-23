"""Pre-event warm-up threads — topic-based group discussions."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.message import Thread, ThreadPost
from app.models.attendee import Attendee
from app.core.deps import require_auth
from app.models.user import User

router = APIRouter(prefix="/threads", tags=["threads"])

# ── 11 default vertical threads ──────────────────────────────────────────────
DEFAULT_THREADS = [
    ("tokenisation_of_finance", "Tokenisation & RWA", "Real-world assets, security tokens, and the future of tokenised finance."),
    ("infrastructure_and_scaling", "Infrastructure & Scaling", "Layer 2s, rollups, bridging, and the plumbing that makes Web3 work at scale."),
    ("decentralized_finance", "DeFi", "Lending, DEXs, stablecoins, and the evolution of decentralised financial services."),
    ("ai_depin_frontier_tech", "AI, DePIN & Frontier Tech", "Where AI meets crypto — decentralised compute, DePIN networks, and frontier applications."),
    ("policy_regulation_macro", "Policy, Regulation & Macro", "MiCA, CBDCs, institutional frameworks, and the regulatory landscape shaping Web3."),
    ("ecosystem_and_foundations", "Ecosystems & Foundations", "Grants, developer relations, community building, and growing Web3 ecosystems."),
    ("investment_and_capital_markets", "Investment & Capital Markets", "Fund strategies, deal flow, LP/GP dynamics, and capital allocation in digital assets."),
    ("culture_media_gaming", "Culture, Media & Gaming", "NFTs, gaming economies, creator tools, and the cultural layer of Web3."),
    ("bitcoin", "Bitcoin", "Bitcoin L2s, ordinals, mining, institutional adoption, and the OG chain."),
    ("prediction_markets", "Prediction Markets", "Information markets, event contracts, and decentralised forecasting."),
    ("decentralized_ai", "Decentralised AI", "On-chain inference, federated learning, AI DAOs, and open-source AI infrastructure."),
]


async def _ensure_default_threads(db: AsyncSession) -> None:
    """Create default vertical threads if they don't exist."""
    existing = await db.execute(select(Thread.slug))
    existing_slugs = {row[0] for row in existing.fetchall()}
    for slug, title, desc in DEFAULT_THREADS:
        if slug not in existing_slugs:
            db.add(Thread(slug=slug, title=title, description=desc))
    await db.commit()


# ── Schemas ──────────────────────────────────────────────────────────────────

class ThreadSummary(BaseModel):
    id: str
    slug: str
    title: str
    description: str | None
    post_count: int
    latest_post_at: str | None
    is_member: bool  # attendee has this vertical_tag

class ThreadPostOut(BaseModel):
    id: str
    sender_name: str
    sender_title: str
    sender_company: str
    sender_attendee_id: str
    content: str
    created_at: str
    is_mine: bool

class PostRequest(BaseModel):
    content: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("")
async def list_threads(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List all warm-up threads with post counts. Attendee's verticals are flagged."""
    await _ensure_default_threads(db)

    attendee = await db.get(Attendee, user.attendee_id) if user.attendee_id else None
    my_verticals = set(attendee.vertical_tags or []) if attendee else set()

    threads = (await db.execute(select(Thread).order_by(Thread.title))).scalars().all()

    summaries = []
    for t in threads:
        # Post count
        count_result = await db.execute(
            select(func.count(ThreadPost.id)).where(ThreadPost.thread_id == t.id)
        )
        post_count = count_result.scalar() or 0

        # Latest post
        latest_result = await db.execute(
            select(ThreadPost.created_at)
            .where(ThreadPost.thread_id == t.id)
            .order_by(ThreadPost.created_at.desc())
            .limit(1)
        )
        latest_row = latest_result.first()
        latest_at = latest_row[0].isoformat() if latest_row else None

        summaries.append(ThreadSummary(
            id=str(t.id),
            slug=t.slug,
            title=t.title,
            description=t.description,
            post_count=post_count,
            latest_post_at=latest_at,
            is_member=t.slug in my_verticals,
        ))

    # Sort: member threads first, then by post count
    summaries.sort(key=lambda s: (not s.is_member, -s.post_count))
    return {"threads": summaries}


@router.get("/{slug}")
async def get_thread(
    slug: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get a thread's posts."""
    thread = (await db.execute(select(Thread).where(Thread.slug == slug))).scalars().first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    attendee = await db.get(Attendee, user.attendee_id) if user.attendee_id else None

    posts_result = await db.execute(
        select(ThreadPost)
        .where(ThreadPost.thread_id == thread.id)
        .order_by(ThreadPost.created_at.asc())
        .limit(limit)
    )
    posts = posts_result.scalars().all()

    post_outputs = []
    for p in posts:
        sender = await db.get(Attendee, p.sender_attendee_id)
        post_outputs.append(ThreadPostOut(
            id=str(p.id),
            sender_name=sender.name if sender else "Unknown",
            sender_title=sender.title if sender else "",
            sender_company=sender.company if sender else "",
            sender_attendee_id=str(p.sender_attendee_id),
            content=p.content,
            created_at=p.created_at.isoformat(),
            is_mine=attendee is not None and p.sender_attendee_id == attendee.id,
        ))

    return {
        "thread": {
            "id": str(thread.id),
            "slug": thread.slug,
            "title": thread.title,
            "description": thread.description,
        },
        "posts": post_outputs,
    }


@router.post("/{slug}")
async def create_post(
    slug: str,
    data: PostRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Post a message to a warm-up thread."""
    if not user.attendee_id:
        raise HTTPException(status_code=400, detail="No attendee profile linked")

    thread = (await db.execute(select(Thread).where(Thread.slug == slug))).scalars().first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Post cannot be empty")
    if len(content) > 2000:
        raise HTTPException(status_code=400, detail="Post too long (max 2000 chars)")

    attendee = await db.get(Attendee, user.attendee_id)

    post = ThreadPost(
        thread_id=thread.id,
        sender_attendee_id=user.attendee_id,
        content=content,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    return ThreadPostOut(
        id=str(post.id),
        sender_name=attendee.name if attendee else "Unknown",
        sender_title=attendee.title if attendee else "",
        sender_company=attendee.company if attendee else "",
        sender_attendee_id=str(post.sender_attendee_id),
        content=post.content,
        created_at=post.created_at.isoformat(),
        is_mine=True,
    )

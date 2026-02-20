import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Enum as SAEnum, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from pgvector.sqlalchemy import Vector
from app.core.database import Base
import enum


class TicketType(str, enum.Enum):
    DELEGATE = "delegate"
    SPONSOR = "sponsor"
    SPEAKER = "speaker"
    VIP = "vip"


class Attendee(Base):
    __tablename__ = "attendees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Registration data
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    company: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255))
    ticket_type: Mapped[TicketType] = mapped_column(SAEnum(TicketType), default=TicketType.DELEGATE)
    interests: Mapped[list] = mapped_column(ARRAY(String), default=list)
    goals: Mapped[str] = mapped_column(Text, nullable=True)  # "What do you want from this event?"

    # Enriched data (populated by enrichment pipeline)
    linkedin_url: Mapped[str] = mapped_column(String(500), nullable=True)
    twitter_handle: Mapped[str] = mapped_column(String(255), nullable=True)
    company_website: Mapped[str] = mapped_column(String(500), nullable=True)
    enriched_profile: Mapped[dict] = mapped_column(JSONB, default=dict)  # Full enriched data blob

    # AI-generated fields
    ai_summary: Mapped[str] = mapped_column(Text, nullable=True)  # AI-generated profile summary
    embedding: Mapped[list] = mapped_column(Vector(1536), nullable=True)  # OpenAI embedding
    intent_tags: Mapped[list] = mapped_column(ARRAY(String), default=list)  # AI-classified intents
    deal_readiness_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-1 score

    # Data intelligence extras
    crunchbase_data: Mapped[dict] = mapped_column(JSONB, default=dict)  # Crunchbase/PitchBook data
    pot_history: Mapped[dict] = mapped_column(JSONB, default=dict)   # Previous POT event attendance
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # Last enrichment run


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    attendee_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    attendee_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)

    # Match quality
    similarity_score: Mapped[float] = mapped_column(Float)  # Vector cosine similarity
    complementary_score: Mapped[float] = mapped_column(Float)  # AI-assessed complementarity
    overall_score: Mapped[float] = mapped_column(Float)  # Weighted final score
    match_type: Mapped[str] = mapped_column(String(50))  # "complementary", "non_obvious", "deal_ready"

    # AI explanation
    explanation: Mapped[str] = mapped_column(Text)  # Why these two should meet
    shared_context: Mapped[dict] = mapped_column(JSONB, default=dict)  # Shared interests, sectors, etc.

    # Status — overall (computed) + per-party
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, accepted, declined, met
    # Two-sided consent: each party's independent response
    status_a: Mapped[str] = mapped_column(String(50), default="pending")  # attendee_a's response
    status_b: Mapped[str] = mapped_column(String(50), default="pending")  # attendee_b's response

    # Scheduling
    meeting_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    meeting_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

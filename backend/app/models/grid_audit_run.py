import uuid
from datetime import datetime
from sqlalchemy import Integer, Float, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base


class GridAuditRun(Base):
    __tablename__ = "grid_audit_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    total_domains: Mapped[int] = mapped_column(Integer)
    total_attendees: Mapped[int] = mapped_column(Integer)
    matched_domains: Mapped[int] = mapped_column(Integer)
    matched_attendees: Mapped[int] = mapped_column(Integer)
    had_grid_before_count: Mapped[int] = mapped_column(Integer, default=0)
    new_matches: Mapped[list] = mapped_column(JSONB, default=list)
    unmatched_domains: Mapped[list] = mapped_column(JSONB, default=list)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

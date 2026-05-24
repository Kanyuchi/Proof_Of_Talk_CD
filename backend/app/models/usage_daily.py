from datetime import date
from sqlalchemy import Date, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class UsageDaily(Base):
    """One snapshot row per UTC day, written by the daily usage cron. Captures
    the per-day history that overwriting last_login_at/last_seen_at would lose.
    See docs/superpowers/specs/2026-05-24-adoption-usage-tracking-design.md.
    """
    __tablename__ = "usage_daily"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    total_accounts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    real_accounts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    active_today: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cumulative_active: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

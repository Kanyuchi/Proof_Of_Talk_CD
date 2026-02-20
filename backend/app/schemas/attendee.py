from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime


class AttendeeCreate(BaseModel):
    name: str
    email: str
    company: str
    title: str
    ticket_type: str = "delegate"
    interests: list[str] = []
    goals: str | None = None
    seeking: list[str] = []
    not_looking_for: list[str] = []
    preferred_geographies: list[str] = []
    deal_stage: str | None = None
    linkedin_url: str | None = None
    twitter_handle: str | None = None
    company_website: str | None = None


class AttendeeResponse(BaseModel):
    id: UUID
    name: str
    email: str
    company: str
    title: str
    ticket_type: str
    interests: list[str]
    goals: str | None
    seeking: list[str]
    not_looking_for: list[str]
    preferred_geographies: list[str]
    deal_stage: str | None
    linkedin_url: str | None
    twitter_handle: str | None
    company_website: str | None
    ai_summary: str | None
    intent_tags: list[str]
    deal_readiness_score: float | None
    enriched_profile: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AttendeeListResponse(BaseModel):
    attendees: list[AttendeeResponse]
    total: int


class MatchResponse(BaseModel):
    id: UUID
    attendee_a_id: UUID
    attendee_b_id: UUID
    similarity_score: float
    complementary_score: float
    overall_score: float
    match_type: str
    explanation: str
    shared_context: dict
    status: str
    status_a: str
    status_b: str
    meeting_time: datetime | None = None
    meeting_location: str | None = None
    met_at: datetime | None = None
    meeting_outcome: str | None = None
    satisfaction_score: float | None = None
    decline_reason: str | None = None
    hidden_by_user: bool = False
    explanation_confidence: float | None = None
    created_at: datetime

    # Populated in the endpoint
    matched_attendee: AttendeeResponse | None = None

    model_config = {"from_attributes": True}


class MatchListResponse(BaseModel):
    matches: list[MatchResponse]
    attendee_id: UUID


class MatchStatusUpdate(BaseModel):
    status: str  # accepted, declined
    decline_reason: str | None = None


class ScheduleMeetingRequest(BaseModel):
    meeting_time: datetime
    meeting_location: str | None = None


class MatchFeedbackUpdate(BaseModel):
    meeting_outcome: str | None = None
    satisfaction_score: float | None = None
    met_at: datetime | None = None
    hidden_by_user: bool | None = None


class DashboardStats(BaseModel):
    total_attendees: int
    matches_generated: int
    matches_accepted: int
    matches_declined: int
    enrichment_coverage: float
    avg_match_score: float
    mutual_accept_rate: float = 0.0
    scheduled_rate: float = 0.0
    show_rate: float = 0.0
    post_meeting_satisfaction: float = 0.0
    top_sectors: list[dict]
    match_type_distribution: dict

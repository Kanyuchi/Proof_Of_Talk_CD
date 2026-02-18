from pydantic import BaseModel
from uuid import UUID


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    # Account credentials
    email: str
    password: str
    # Attendee profile
    name: str
    company: str
    title: str
    ticket_type: str = "delegate"
    interests: list[str] = []
    goals: str | None = None
    linkedin_url: str | None = None
    twitter_handle: str | None = None
    company_website: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    is_admin: bool
    attendee_id: UUID | None

    model_config = {"from_attributes": True}

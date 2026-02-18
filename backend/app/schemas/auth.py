from pydantic import BaseModel, field_validator, EmailStr
from uuid import UUID
import re


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    # Account credentials
    email: EmailStr
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

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("name", "company", "title")
    @classmethod
    def no_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be blank")
        return v.strip()


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

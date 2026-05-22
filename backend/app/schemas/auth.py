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
    company: str = ""
    title: str = ""
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
    privacy_mode: str = "full"  # "full" or "b2b_only"

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

    @field_validator("name")
    @classmethod
    def no_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be blank")
        return v.strip()


class JoinRequest(BaseModel):
    """Self-service sponsor onboarding via the shared invite link. Same profile
    fields as RegisterRequest plus `invite_code`; `ticket_type` defaults to
    SPONSOR and is forced server-side regardless."""
    invite_code: str
    # Account credentials
    email: EmailStr
    password: str
    # Attendee profile
    name: str
    company: str = ""
    title: str = ""
    ticket_type: str = "SPONSOR"
    interests: list[str] = []
    goals: str | None = None
    target_companies: str | None = None
    seeking: list[str] = []
    not_looking_for: list[str] = []
    preferred_geographies: list[str] = []
    deal_stage: str | None = None
    linkedin_url: str | None = None
    twitter_handle: str | None = None
    company_website: str | None = None
    privacy_mode: str = "full"

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

    @field_validator("name")
    @classmethod
    def no_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be blank")
        return v.strip()


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ClaimAccountRequest(BaseModel):
    """Convert an existing attendee row (identified by its magic-link token)
    into a full login. The token is the proof of ownership, so this bypasses
    the registration ticket gate. `email` is optional — required only when the
    attendee's current email is a placeholder (e.g. @speaker.proofoftalk.io)."""
    magic_token: str
    password: str
    email: EmailStr | None = None

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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
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


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    is_admin: bool
    attendee_id: UUID | None

    model_config = {"from_attributes": True}

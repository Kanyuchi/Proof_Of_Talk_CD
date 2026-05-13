from typing import Literal

from pydantic import BaseModel, Field

OfferableField = Literal["goals", "target_companies", "interests"]


class ChatMessageSchema(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    attendee_id: str | None = None
    history: list[ChatMessageSchema] = []


class ChatResponse(BaseModel):
    response: str


class ProfilePromptResponse(BaseModel):
    """Returned by GET /chat/profile-prompt.

    `field` is null when no offer should fire (profile already ≥80% complete,
    or all candidate fields are filled / recently declined).
    """
    field: OfferableField | None = None
    current_completeness_pct: int = 0
    is_sparse: bool = False  # true when LinkedIn headline + ai_summary stub mean GPT will return 2 generic candidates


class DraftFieldRequest(BaseModel):
    field: OfferableField


class DraftFieldResponse(BaseModel):
    candidates: list[str] = Field(default_factory=list)
    is_sparse: bool = False  # echoed so the UI can show the "starting points — feel free to rewrite" hint


class SaveFieldRequest(BaseModel):
    field: OfferableField
    value: str


class DeclinePromptRequest(BaseModel):
    field: OfferableField

from pydantic import BaseModel


class ChatMessageSchema(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    attendee_id: str | None = None
    history: list[ChatMessageSchema] = []


class ChatResponse(BaseModel):
    response: str

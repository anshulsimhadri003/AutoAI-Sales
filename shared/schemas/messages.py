from pydantic import BaseModel

class AIReplyRequest(BaseModel):
    lead_id: str | None = None
    message: str

class AIReplyResponse(BaseModel):
    reply: str

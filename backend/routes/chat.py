from pydantic import BaseModel, Field
from fastapi import APIRouter

from services.rag_pipeline import get_rag_pipeline


router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str = Field(min_length=1)


class ChatResponse(BaseModel):
    answer: str
    intent: str
    confidence: float
    urgency: str
    emotion: str
    resolved: bool
    sources: list[str]
    booking_status: str
    booking_id: str
    booked_slot: str
    booked_department: str
    patient_name: str


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    pipeline = get_rag_pipeline()
    result = pipeline.handle_query(message=payload.message, session_id=payload.session_id)
    return ChatResponse(**result)

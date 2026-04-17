from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.rag_pipeline import get_rag_pipeline
from services.report_generator import ReportGenerator


router = APIRouter()
report_generator = ReportGenerator()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    next_question: str = ""
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
    possible_conditions: list[str] = Field(default_factory=list)
    disease_prediction: str = ""
    icd_matches: list[dict] = Field(default_factory=list)


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    pipeline = get_rag_pipeline()
    result = pipeline.handle_query(message=payload.message, session_id=payload.session_id)
    return ChatResponse(**result)


@router.get("/report/{session_id}")
def download_chat_report(session_id: str) -> StreamingResponse:
    pipeline = get_rag_pipeline()
    session_payload = pipeline.get_session_report_context(session_id)
    if not session_payload.get("messages"):
        raise HTTPException(status_code=404, detail="No chat history found for this session.")

    pdf_bytes = report_generator.build_pdf(session_payload)
    filename = f"medical-chat-report-{session_id}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(iter([pdf_bytes]), media_type="application/pdf", headers=headers)

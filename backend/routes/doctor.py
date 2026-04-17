from __future__ import annotations

from fastapi import APIRouter

from services.rag_pipeline import get_rag_pipeline


router = APIRouter()


@router.get("/appointments")
def doctor_appointments() -> dict:
    pipeline = get_rag_pipeline()
    return {"appointments": pipeline.get_doctor_dashboard_data()}

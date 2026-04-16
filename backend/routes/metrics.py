from fastapi import APIRouter

from services.rag_pipeline import get_rag_pipeline


router = APIRouter()


@router.get("")
def get_metrics() -> dict:
    pipeline = get_rag_pipeline()
    return pipeline.get_metrics()

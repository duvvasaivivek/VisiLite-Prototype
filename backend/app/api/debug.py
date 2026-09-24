from fastapi import APIRouter
from app.core.config import settings
router = APIRouter()
@router.get("/debug")
def debug():
    return {"model": settings.llm_model, "key_len": len(settings.llm_api_key)}

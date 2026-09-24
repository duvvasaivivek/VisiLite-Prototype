from fastapi import APIRouter, HTTPException
from app.agent.llm import LLMUnavailable, plan_action
from app.models.schemas import SanitizedContext, SanitizedElement, Sensitivity
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class ExtensionElement(BaseModel):
    id: str
    tag: str
    type: Optional[str] = None
    role: Optional[str] = None
    text: str = ""
    value: str = ""
    placeholder: str = ""

class ExtensionContext(BaseModel):
    url: str
    title: str
    elements: list[ExtensionElement]

class ExtensionPlanRequest(BaseModel):
    task: str
    context: ExtensionContext
    history: list[str] = []

@router.get("/health")
async def health():
    return {"status": "ok", "agent": "idle", "browser_ready": True}

@router.post("/plan")
async def extension_plan(req: ExtensionPlanRequest):
    elements = []
    for el in req.context.elements:
        elements.append(SanitizedElement(
            id=el.id,
            role=el.role or "",
            label=el.placeholder or el.text,
            type=el.type or "",
            tag=el.tag,
            text=el.text,
            value=el.value,
            sensitivity=Sensitivity.PUBLIC
        ))
    
    sanitized_ctx = SanitizedContext(
        page_title=req.context.title,
        url=req.context.url,
        task=req.task,
        elements=elements,
        available_user_tokens={}
    )
    
    history_str = "Previous actions taken in this task loop: " + ", ".join(req.history) if req.history else ""
    try:
        return plan_action(sanitized_ctx, extra=history_str)
    except LLMUnavailable:
        raise HTTPException(503, "AI reasoning unavailable")

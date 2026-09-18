from fastapi import APIRouter, HTTPException

from app.agent.guard import action_guard
from app.agent.llm import LLMUnavailable, plan_action
from app.agent.orchestrator import orchestrator
from app.audit.log import audit
from app.browser.adapter import browser_adapter
from app.core.config import settings
from app.core.metrics import metrics
from app.models.schemas import (
    HealthResponse,
    PrivacyAnalyzeRequest,
    SanitizedContext,
    TaskCreate,
)
from app.perception.ocr import OCR_EVENTS, get_reader, reader_load_count
from app.privacy.detector import detect_hybrid
from app.privacy.profile import load_profile, tokenize_profile
from app.privacy.sanitizer import build_sanitized_context
from app.privacy.vault import vault
from app.perception.engine import perception_engine

router = APIRouter()


@router.get("/system/health", response_model=HealthResponse)
async def health():
    ocr_loaded = False
    try:
        ocr_loaded = get_reader() is not None or reader_load_count() > 0
    except Exception:
        ocr_loaded = False
    llm_available = settings.llm_provider == "local" or bool(settings.llm_api_key)
    return HealthResponse(
        status="ok",
        llm_provider=settings.llm_provider,
        llm_available=llm_available,
        ocr_enabled=settings.enable_ocr,
        ocr_loaded=bool(ocr_loaded),
        browser_ready=browser_adapter.ready,
        privacy_gateway="local",
    )


@router.post("/tasks")
async def create_task(body: TaskCreate):
    return await orchestrator.create_task(body.instruction, body.start_url)


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    try:
        return orchestrator.get(task_id)
    except KeyError:
        raise HTTPException(404, "task not found")


@router.post("/tasks/{task_id}/approve")
async def approve_task(task_id: str, allow: bool = True):
    return await orchestrator.approve(task_id, allow)


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    return await orchestrator.cancel(task_id)


@router.get("/browser/state")
async def browser_state():
    return await browser_adapter.state()


@router.post("/privacy/analyze")
async def privacy_analyze(body: PrivacyAnalyzeRequest):
    findings = detect_hybrid(body.text, body.field_name, body.html_context)
    return {
        "findings": [
            {
                "entity_type": f.entity_type,
                "value_tokenized": vault.tokenize(f.value, f.entity_type, f.sensitivity) if f.value else "",
                "sensitivity": f.sensitivity,
                "detector": f.detector,
            }
            for f in findings
        ]
    }


@router.post("/privacy/sanitize")
async def privacy_sanitize(instruction: str = "inspect page"):
    if not browser_adapter.ready:
        await browser_adapter.start()
    page = await perception_engine.perceive(browser_adapter, instruction)
    tokens = tokenize_profile(load_profile())
    context = build_sanitized_context(page, instruction, tokens)
    return context


@router.post("/agent/plan")
async def agent_plan(context: SanitizedContext):
    try:
        return plan_action(context)
    except LLMUnavailable:
        raise HTTPException(503, "AI reasoning unavailable")


@router.post("/actions/validate")
async def actions_validate(raw: dict):
    if not browser_adapter.ready:
        raise HTTPException(503, "Browser unavailable")
    page = await perception_engine.perceive(browser_adapter, "validate")
    return action_guard.validate(raw, page, page.url)


@router.post("/actions/execute")
async def actions_execute(raw: dict):
    page = await perception_engine.perceive(browser_adapter, "execute")
    decision = action_guard.validate(raw, page, page.url)
    if not decision.approved or not decision.action:
        return decision
    resolved = action_guard.resolve_tokens(decision.action)
    if resolved.action.value == "fill":
        await browser_adapter.fill(resolved.element_id or "", resolved.value or "")
    elif resolved.action.value == "click":
        await browser_adapter.click(resolved.element_id or "")
    return {"executed": True, "guard": decision}


@router.get("/audit/logs")
async def audit_logs():
    return audit.all()


@router.get("/privacy/statistics")
async def privacy_statistics():
    snap = metrics.snapshot()
    return {
        "pii_detected_locally": snap["pii_detected"],
        "pii_tokenized": snap["pii_tokenized"],
        "raw_pii_sent_to_ai": snap["raw_pii_sent_to_ai"],
        "sanitized_context_sent": snap["sanitized_context_sent"] > 0,
        "blocked_actions": snap["blocked_actions"],
    }


@router.get("/performance/statistics")
async def performance_statistics():
    data = metrics.snapshot()
    data["ocr_events"] = OCR_EVENTS[-20:]
    data["ocr_model_load_count"] = reader_load_count()
    return data

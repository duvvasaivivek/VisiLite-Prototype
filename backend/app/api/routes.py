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
    name: Optional[str] = None
    text: str = ""
    value: str = ""
    placeholder: str = ""
    ariaLabel: Optional[str] = None
    label: Optional[str] = None
    describedBy: Optional[str] = None
    href: Optional[str] = None
    checked: Optional[bool] = None
    disabled: bool = False

class ExtensionContext(BaseModel):
    url: str
    title: str
    elements: list[ExtensionElement]
    pageTextSample: str = ""
    elementCount: int = 0

class ExtensionPlanRequest(BaseModel):
    task: str
    context: ExtensionContext
    history: list[str] = []

from app.models.schemas import HealthResponse, PrivacyAnalyzeRequest

@router.get("/system/health", response_model=HealthResponse)
async def health():
    from app.core.config import settings
    return HealthResponse(
        status="ok",
        llm_provider=settings.llm_provider,
        llm_available=True,
        ocr_enabled=settings.enable_ocr,
        ocr_loaded=True,
        browser_ready=True,
        privacy_gateway="local"
    )

@router.post("/privacy/analyze")
async def analyze_privacy(req: PrivacyAnalyzeRequest):
    from app.privacy.detector import detect_hybrid
    findings = detect_hybrid(req.text, req.html_context, req.field_name)
    return {"findings": [{"type": f.entity_type, "match": f.match_string, "sensitivity": f.sensitivity.value} for f in findings]}

@router.post("/plan")
async def extension_plan(req: ExtensionPlanRequest):
    elements = []
    for el in req.context.elements:
        # Build the richest possible label by combining all semantic sources
        resolved_label = el.ariaLabel or el.label or el.placeholder or el.text or ""

        elements.append(SanitizedElement(
            id=el.id,
            role=el.role or "",
            label=resolved_label,
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
        import os, json, re
        from app.security.vault import vault, VaultLockedError, VaultItemNotFoundError

        # For prototype purposes: auto-unlock the vault in this process
        if vault.is_locked():
            pwd = os.getenv("VAULT_PASSWORD")
            if pwd:
                try:
                    vault.unlock(pwd)
                    print("VAULT UNLOCKED:", not vault.is_locked())
                except Exception as e:
                    print("VAULT UNLOCK FAILED:", e)

        # Provide available tokens to the LLM context so it knows what it can ask for
        if not vault.is_locked():
            vault_file = os.path.join(os.path.dirname(__file__), '..', 'security', 'vault.json')
            if os.path.exists(vault_file):
                with open(vault_file, 'r') as f:
                    data = json.load(f)
                    sanitized_ctx.available_user_tokens = {k: f"<VAULT_TOKEN: {k}>" for k in data.get("items", {}).keys()}
                    print("TOKENS SENT TO AI:", sanitized_ctx.available_user_tokens)
        else:
            print("VAULT IS STILL LOCKED!")

        action_plan = plan_action(sanitized_ctx, extra=history_str)
        
        # PRIVACY GATEWAY: Intercept and decrypt vault tokens
        if action_plan.action == "fill" and action_plan.value:
            value = action_plan.value
            
            # Find all tokens in the format <VAULT_TOKEN: Key>
            matches = list(re.finditer(r'<VAULT_TOKEN:\s*(.+?)>', value))
            
            for match in matches:
                token_key = match.group(1).strip()
                try:
                    real_value = vault.get(token_key)
                    # Replace this specific token with the real value
                    value = value.replace(match.group(0), real_value)
                except VaultLockedError:
                    raise HTTPException(403, detail="Vault is locked. Cannot fulfill token request.")
                except VaultItemNotFoundError:
                    raise HTTPException(400, detail=f"Requested token '{token_key}' not found in vault.")
            
            action_plan.value = value
            
        # 6. ACTION GUARD: Assess risk and pause if HIGH
        from app.security.guard import guard
        risk_level = guard.assess_risk(action_plan, sanitized_ctx)
        
        if risk_level == "HIGH":
            # Wrap the action in an 'ask_permission' request
            original_action_json = action_plan.model_dump_json()
            el = next((e for e in sanitized_ctx.elements if e.id == action_plan.element_id), None)
            el_text = (el.text or el.label or el.value or action_plan.element_id) if el else action_plan.element_id
            
            action_plan.action = "ask_permission"
            action_plan.value = original_action_json
            action_plan.reason = f"Agent is about to click [{el_text}]. Approve? (Y/N)"
                    
        return action_plan
    except LLMUnavailable:
        raise HTTPException(503, detail="AI reasoning unavailable")

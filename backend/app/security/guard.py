from app.models.schemas import StructuredAction, SanitizedContext

class ActionGuard:
    def __init__(self):
        self.high_risk_keywords = ["pay", "delete", "confirm", "place order", "checkout", "buy"]

    def assess_risk(self, action_plan: StructuredAction, context: SanitizedContext) -> str:
        if action_plan.action in ["navigate", "scroll", "extract", "finish", "wait", "fail"]:
            return "LOW"
            
        if action_plan.action in ["fill", "select"]:
            return "MEDIUM"
            
        if action_plan.action in ["click", "enter"]:
            if action_plan.element_id:
                # Find the element to check its text
                el = next((e for e in context.elements if e.id == action_plan.element_id), None)
                if el:
                    text = (el.text or el.label or el.value or "").lower()
                    for kw in self.high_risk_keywords:
                        if kw in text:
                            return "HIGH"
                            
            return "MEDIUM"
            
        return "MEDIUM"
        
    def validate(self, action_dict: dict, page, current_url: str):
        from app.models.schemas import ActionDecision, StructuredAction, AgentActionType
        from app.security.domains import assert_allowed
        
        try:
            action_val = action_dict.get("action")
            action = StructuredAction(**action_dict)
        except Exception as e:
            return ActionDecision(approved=False, blocked=True, reason="Malformed action payload (schema validation failed)")
            
        if action.url:
            ok, reason = assert_allowed(action.url)
            if not ok:
                return ActionDecision(approved=False, blocked=True, reason=reason)
                
        if action.element_id:
            el = next((e for e in page.elements if e.id == action.element_id), None)
            if not el:
                return ActionDecision(approved=False, blocked=True, reason=f"Element {action.element_id} not found on page")
            if not el.visible:
                return ActionDecision(approved=False, blocked=True, reason=f"Element {action.element_id} is not visible")
            if not el.enabled:
                return ActionDecision(approved=False, blocked=True, reason=f"Element {action.element_id} is not interactable")
                
        # Check for unauthorized transmission or hallucinated token
        if action.value and "<" in action.value and ">" in action.value:
            from app.privacy.vault import vault
            # Extract token using simple check
            import re
            tokens = re.findall(r"<[^>]+>", action.value)
            for t in tokens:
                if not vault.resolve(t) or vault.resolve(t) == t:
                    return ActionDecision(approved=False, blocked=True, reason=f"Hallucinated or invalid token {t}")
            
            if "external" in action.reason.lower() or action.action != AgentActionType.fill:
                return ActionDecision(approved=False, blocked=True, reason="Privacy boundary violation: Cannot send protected tokens to unauthorized destinations")

        return ActionDecision(approved=True, action=action)
        
    def resolve_tokens(self, action):
        from app.privacy.vault import vault
        action_copy = action.model_copy() if hasattr(action, "model_copy") else action.copy()
        if action_copy.value and isinstance(action_copy.value, str):
            import re
            tokens = re.findall(r"<[^>]+>", action_copy.value)
            for t in tokens:
                action_copy.value = action_copy.value.replace(t, vault.resolve(t) or t)
        return action_copy

guard = ActionGuard()

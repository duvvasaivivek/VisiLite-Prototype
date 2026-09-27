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

guard = ActionGuard()

from app.privacy.detector import detect_hybrid

class PolicyEngine:
    def check_text(self, text: str, context_str: str = "", input_type: str = ""):
        return detect_hybrid(text, context_str, input_type)

policy_engine = PolicyEngine()
__all__ = ["policy_engine"]

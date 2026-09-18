from __future__ import annotations

from typing import Optional

from app.agent.llm import LocalPlanner
from app.models.schemas import SanitizedContext, StructuredAction


def deterministic_action(context: SanitizedContext) -> Optional[StructuredAction]:
    """Use structured DOM/token matching without calling an external model."""
    planner = LocalPlanner()
    action = planner.plan(context)
    if action.action.value in {"fill", "click", "wait"}:
        # LocalPlanner increments llm_calls; roll back for deterministic path.
        from app.core.metrics import metrics

        metrics.add(llm_calls=-1)
        action.reason = f"deterministic: {action.reason}"
        return action
    if action.action.value == "finish":
        from app.core.metrics import metrics

        metrics.add(llm_calls=-1)
        return action
    return None

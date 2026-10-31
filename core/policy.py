"""Approval policy from the VASIKO architecture."""
from __future__ import annotations

from dataclasses import dataclass

from .domain import RiskLevel

SAFE_INTERNAL_ACTIONS = frozenset({
    "analyze", "draft", "calculate", "test_in_isolation", "create_report",
    "create_checkpoint", "run_diagnostics", "create_backup",
})

REQUIRES_APPROVAL = frozenset({
    "payment", "publication", "send_message", "create_account", "access_personal_data",
    "send_document", "order", "change_website", "start_paid_service", "external_action",
})


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    requires_approval: bool
    reason: str


def evaluate_action(action: str, risk: RiskLevel | None = None) -> PolicyDecision:
    normalized = (action or "").strip().lower()
    if normalized in SAFE_INTERNAL_ACTIONS and risk != RiskLevel.DESTRUCTIVE:
        return PolicyDecision(True, False, "Разрешено как безопасное внутреннее действие")
    if normalized in REQUIRES_APPROVAL or risk in {RiskLevel.EXTERNAL, RiskLevel.DESTRUCTIVE}:
        return PolicyDecision(False, True, "Требуется отдельное подтверждение пользователя")
    return PolicyDecision(False, True, "Неизвестное действие блокируется до явного approval")

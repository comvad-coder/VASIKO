from core.domain import RiskLevel
from core.policy import evaluate_action


def test_safe_internal_action_is_allowed():
    decision = evaluate_action("analyze")
    assert decision.allowed is True
    assert decision.requires_approval is False


def test_external_action_requires_approval():
    decision = evaluate_action("publication")
    assert decision.allowed is False
    assert decision.requires_approval is True


def test_unknown_action_is_fail_closed():
    decision = evaluate_action("unknown-action")
    assert decision.allowed is False
    assert decision.requires_approval is True


def test_destructive_risk_overrides_safe_name():
    decision = evaluate_action("analyze", RiskLevel.DESTRUCTIVE)
    assert decision.allowed is False
    assert decision.requires_approval is True

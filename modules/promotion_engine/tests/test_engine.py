import pytest

from modules.promotion_engine import (
    PlanStatus,
    PromotionBrief,
    PromotionEngine,
    PromotionEngineError,
)


def brief(**overrides):
    values = {
        "task_id": "palmistry-pilot",
        "product_id": "palm",
        "product_name": "Palm",
        "product_url": "https://palm.example",
        "description": "A product for a visual audience",
        "audience": ["visual", "social"],
        "regions": ["US"],
        "available_assets": ["video_demo"],
    }
    values.update(overrides)
    return PromotionBrief(**values)


def test_plan_selects_two_channels_without_external_calls():
    plan = PromotionEngine().build_plan(brief())

    assert plan.status is PlanStatus.DRAFT
    assert len(plan.selected_channels) == 2
    assert plan.approval_required is True
    assert plan.external_actions_enabled is False
    assert plan.selected_channels[0] in {"short_video", "instagram", "tiktok"}
    assert "user_approval" in plan.phases


def test_plan_can_move_to_approval_but_not_execute():
    engine = PromotionEngine()
    awaiting = engine.request_approval(engine.build_plan(brief()))
    assert awaiting.status is PlanStatus.AWAITING_APPROVAL
    with pytest.raises(PromotionEngineError, match="stubbed"):
        engine.execute(awaiting)


def test_invalid_url_and_missing_fields_are_rejected():
    with pytest.raises(PromotionEngineError, match=r"http\(s\)"):
        PromotionEngine().build_plan(brief(product_url="localhost:5678"))
    with pytest.raises(PromotionEngineError, match="product_name"):
        PromotionEngine().build_plan(brief(product_name=""))


def test_plan_is_serializable_without_secrets():
    plan = PromotionEngine().build_plan(brief())
    payload = plan.to_dict()
    assert payload["status"] == "draft"
    assert payload["external_actions_enabled"] is False
    assert "token" not in str(payload).lower()

"""Local, approval-gated promotion planning module."""

from .engine import (
    ChannelAssessment,
    PlanStatus,
    PromotionBrief,
    PromotionEngine,
    PromotionEngineError,
    PromotionPlan,
)

__all__ = [
    "ChannelAssessment",
    "PlanStatus",
    "PromotionBrief",
    "PromotionEngine",
    "PromotionEngineError",
    "PromotionPlan",
]

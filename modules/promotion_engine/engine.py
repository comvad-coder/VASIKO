"""Deterministic local promotion planning for VASIKO.

This block creates plans only. It does not fetch URLs, call external APIs,
publish content, send messages, or access credentials.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from urllib.parse import urlparse


class PromotionEngineError(ValueError):
    """Raised when a local promotion planning input is invalid."""


class PlanStatus(str, Enum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"


@dataclass(frozen=True)
class PromotionBrief:
    task_id: str
    product_id: str
    product_name: str
    product_url: str
    description: str
    audience: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    available_assets: list[str] = field(default_factory=list)
    existing_channels: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    workspace_id: str = ""

    def validate(self) -> None:
        for field_name in ("task_id", "product_id", "product_name", "description"):
            if not str(getattr(self, field_name)).strip():
                raise PromotionEngineError(f"Promotion brief field is required: {field_name}")
        parsed = urlparse(self.product_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise PromotionEngineError("product_url должен быть корректным http(s) URL")


@dataclass(frozen=True)
class ChannelAssessment:
    channel: str
    score: int
    reasons: list[str]
    risks: list[str]
    required_assets: list[str]


@dataclass(frozen=True)
class PromotionPlan:
    task_id: str
    product_id: str
    status: PlanStatus
    selected_channels: list[str]
    assessments: list[ChannelAssessment]
    phases: list[str]
    approval_required: bool = True
    external_actions_enabled: bool = False

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data


_BASE_CHANNELS = (
    ("short_video", 70, "visual format can demonstrate the product quickly", "video assets and platform adaptations are required", ["short_video_script"]),
    ("seo", 64, "search content can build durable discovery", "results require time and keyword validation", ["landing_page", "keyword_brief"]),
    ("youtube", 58, "longer demonstrations can explain product value", "production effort is higher than short-form content", ["video_outline"]),
    ("telegram", 48, "owned updates can support an interested audience", "requires an existing audience or permission-based acquisition", ["channel_message"]),
    ("instagram", 52, "visual product stories can be adapted to the platform", "platform-specific creative and account approval are required", ["visual_post"]),
    ("tiktok", 55, "short discovery content may reach a relevant audience", "platform policy and creative fit must be checked", ["short_video_script"]),
    ("articles", 50, "educational content can support trust and SEO", "requires editorial research and distribution", ["article_outline"]),
)


class PromotionEngine:
    """Builds a reviewable local plan; external execution remains disabled."""

    def build_plan(self, brief: PromotionBrief) -> PromotionPlan:
        brief.validate()
        assessments = [self._assess(brief, channel, base, reason, risk, assets) for channel, base, reason, risk, assets in _BASE_CHANNELS]
        ranked = sorted(assessments, key=lambda item: (-item.score, item.channel))
        selected = [item.channel for item in ranked[:2]]
        return PromotionPlan(
            task_id=brief.task_id,
            product_id=brief.product_id,
            status=PlanStatus.DRAFT,
            selected_channels=selected,
            assessments=ranked,
            phases=[
                "product_analysis",
                "audience_and_competitor_research_stub",
                "channel_strategy_review",
                "content_plan_draft",
                "user_approval",
                "production_after_approval",
                "publication_after_approval",
                "analytics_and_iteration",
            ],
        )

    @staticmethod
    def request_approval(plan: PromotionPlan) -> PromotionPlan:
        if not plan.approval_required:
            raise PromotionEngineError("Promotion plan approval gate cannot be disabled")
        return PromotionPlan(
            task_id=plan.task_id,
            product_id=plan.product_id,
            status=PlanStatus.AWAITING_APPROVAL,
            selected_channels=plan.selected_channels,
            assessments=plan.assessments,
            phases=plan.phases,
            approval_required=True,
            external_actions_enabled=False,
        )

    @staticmethod
    def execute(_plan: PromotionPlan) -> None:
        raise PromotionEngineError("External promotion execution is stubbed until explicit approval and integrations")

    @staticmethod
    def _assess(brief: PromotionBrief, channel: str, base: int, reason: str, risk: str, assets: list[str]) -> ChannelAssessment:
        score = base
        reasons = [reason]
        audience = {item.lower() for item in brief.audience}
        available = {item.lower() for item in brief.available_assets}
        existing = {item.lower() for item in brief.existing_channels}
        if channel in existing:
            score += 8
            reasons.append("channel already exists in the product context")
        if channel in {"short_video", "tiktok", "instagram", "youtube"} and available.intersection({"video", "video_demo", "short_video"}):
            score += 10
            reasons.append("available video asset reduces initial production risk")
        if channel in {"seo", "articles"} and any(item in audience for item in {"search", "educational", "professional"}):
            score += 8
            reasons.append("audience context supports research-led content")
        if channel in {"short_video", "tiktok", "instagram"} and audience.intersection({"visual", "young", "social"}):
            score += 7
            reasons.append("audience context supports visual discovery")
        if channel == "telegram" and audience.intersection({"community", "existing_audience"}):
            score += 9
            reasons.append("audience context supports owned community distribution")
        if not brief.available_assets and channel in {"short_video", "youtube", "instagram", "tiktok"}:
            score -= 8
            reasons.append("no existing media assets; production is still needed")
        return ChannelAssessment(channel, max(0, min(score, 100)), reasons, [risk], assets)

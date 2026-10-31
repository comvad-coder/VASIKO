"""Stable domain vocabulary for VASIKO Core Block 2."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EntityType(str, Enum):
    TASK = "task"
    PRODUCT = "product"
    PROJECT = "project"
    WORKSPACE = "workspace"
    MODULE = "module"
    SKILL = "skill"
    AGENT = "agent"
    INTEGRATION = "integration"
    N8N_WORKFLOW = "n8n_workflow"


class TaskStatus(str, Enum):
    NEW = "new"
    PLANNED = "planned"
    AWAITING_APPROVAL = "awaiting_approval"
    RUNNING = "running"
    CHECKPOINT = "checkpoint"
    QA = "qa"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    ROLLED_BACK = "rolled_back"


class RiskLevel(str, Enum):
    SAFE_INTERNAL = "safe_internal"
    EXTERNAL = "external"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class EntityRef:
    entity_type: EntityType
    entity_id: str


@dataclass
class TaskSpec:
    task_id: str
    objective: str
    status: TaskStatus = TaskStatus.NEW
    project: EntityRef | None = None
    products: list[EntityRef] = field(default_factory=list)
    workspaces: list[EntityRef] = field(default_factory=list)
    plan: str = ""
    checkpoints: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    next_step: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class ApprovalRequest:
    approval_id: str
    task_id: str
    action: str
    risk: RiskLevel
    reason: str
    status: str = "pending"
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    action: str
    actor: str
    details: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class HealthCheck:
    component: str
    status: str
    details: str = ""
    checked_at: str = field(default_factory=utc_now)

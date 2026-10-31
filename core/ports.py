"""Dependency-inversion ports for future Core adapters."""
from __future__ import annotations

from typing import Protocol

from .domain import ApprovalRequest, AuditEvent, HealthCheck, TaskSpec


class TaskRepository(Protocol):
    def save(self, task: TaskSpec) -> None: ...
    def get(self, task_id: str) -> TaskSpec | None: ...


class AuditLog(Protocol):
    def append(self, event: AuditEvent) -> None: ...
    def list_recent(self, limit: int = 100) -> list[AuditEvent]: ...


class ApprovalGateway(Protocol):
    def request(self, request: ApprovalRequest) -> None: ...
    def decide(self, approval_id: str, decision: str) -> None: ...


class HealthProbe(Protocol):
    def check(self) -> HealthCheck: ...

"""Local system-state model for Core diagnostics."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .domain import HealthCheck


@dataclass
class SystemState:
    checks: list[HealthCheck] = field(default_factory=list)

    @property
    def overall_status(self) -> str:
        statuses = {check.status for check in self.checks}
        if "critical" in statuses:
            return "critical"
        if "warning" in statuses:
            return "warning"
        if not statuses:
            return "unknown"
        return "healthy"

    def record(self, check: HealthCheck) -> None:
        self.checks.append(check)


def run_local_diagnostics(runtime_path: str | Path) -> SystemState:
    path = Path(runtime_path)
    state = SystemState()
    state.record(HealthCheck("core", "healthy", "Core contracts loaded"))
    state.record(HealthCheck("runtime_path", "healthy" if path.exists() else "warning", str(path)))
    state.record(HealthCheck("external_integrations", "stubbed", "No external calls in Block 2"))
    state.record(HealthCheck("n8n_gateway", "not_connected", "Gateway belongs to a later block"))
    return state

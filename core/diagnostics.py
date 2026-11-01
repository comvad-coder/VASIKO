"""Local system health checks for VASIKO Block 4."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .backup_manager import BackupManager, BackupError
from .domain import TaskStatus


class DiagnosticStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DiagnosticItem:
    component: str
    status: DiagnosticStatus
    details: str


@dataclass
class HealthReport:
    items: list[DiagnosticItem] = field(default_factory=list)

    @property
    def overall_status(self) -> DiagnosticStatus:
        statuses = {item.status for item in self.items}
        if DiagnosticStatus.CRITICAL in statuses:
            return DiagnosticStatus.CRITICAL
        if DiagnosticStatus.WARNING in statuses:
            return DiagnosticStatus.WARNING
        if not statuses:
            return DiagnosticStatus.UNKNOWN
        return DiagnosticStatus.HEALTHY

    def as_dict(self) -> dict:
        return {"overall_status": self.overall_status.value, "items": [
            {"component": item.component, "status": item.status.value, "details": item.details}
            for item in self.items
        ]}


class SystemDiagnostics:
    def __init__(self, root: str | Path, backup_manager: BackupManager | None = None) -> None:
        self.root = Path(root).resolve()
        self.backup_manager = backup_manager or BackupManager(self.root, self.root / "backups" / "vasiko")

    def run(self) -> HealthReport:
        report = HealthReport()
        self._path_check(report, "core", self.root / "core" / "domain.py")
        self._path_check(report, "gradio_admin", self.root / "admin" / "gradio_admin" / "app.py")
        self._path_check(report, "task_storage", self.root / "tasks" / "records")
        self._path_check(report, "memory_storage", self.root / "memory")
        self._disk_check(report)
        self._task_check(report)
        self._backup_check(report)
        report.items.append(DiagnosticItem("database", DiagnosticStatus.WARNING, "Database adapter is not connected; local JSON is active"))
        report.items.append(DiagnosticItem("n8n_gateway", DiagnosticStatus.WARNING, "n8n gateway is not connected in Block 4"))
        report.items.append(DiagnosticItem("oauth_integrations", DiagnosticStatus.WARNING, "No external OAuth checks are executed"))
        return report

    @staticmethod
    def _path_check(report: HealthReport, name: str, path: Path) -> None:
        status = DiagnosticStatus.HEALTHY if path.exists() else DiagnosticStatus.CRITICAL
        report.items.append(DiagnosticItem(name, status, str(path)))

    def _disk_check(self, report: HealthReport) -> None:
        try:
            usage = shutil.disk_usage(self.root)
            percent = usage.used / usage.total * 100
            status = DiagnosticStatus.CRITICAL if percent >= 95 else DiagnosticStatus.WARNING if percent >= 85 else DiagnosticStatus.HEALTHY
            report.items.append(DiagnosticItem("disk", status, f"{percent:.1f}% used"))
        except OSError as exc:
            report.items.append(DiagnosticItem("disk", DiagnosticStatus.UNKNOWN, str(exc)))

    def _task_check(self, report: HealthReport) -> None:
        records = self.root / "tasks" / "records"
        running = 0
        malformed = 0
        for path in records.glob("*.json") if records.exists() else []:
            try:
                status = json.loads(path.read_text(encoding="utf-8")).get("status")
                running += status == TaskStatus.RUNNING.value
            except (OSError, ValueError, json.JSONDecodeError):
                malformed += 1
        if malformed:
            report.items.append(DiagnosticItem("task_records", DiagnosticStatus.CRITICAL, f"{malformed} malformed task records"))
        else:
            report.items.append(DiagnosticItem("task_records", DiagnosticStatus.HEALTHY, f"{running} running tasks; no malformed records"))

    def _backup_check(self, report: HealthReport) -> None:
        latest = self.backup_manager.latest()
        if latest is None:
            report.items.append(DiagnosticItem("backups", DiagnosticStatus.WARNING, "No backup archive found"))
            return
        try:
            manifest = self.backup_manager.verify(latest)
            report.items.append(DiagnosticItem("backups", DiagnosticStatus.HEALTHY, f"{manifest.archive}; {manifest.file_count} files; SHA-256 verified"))
        except BackupError as exc:
            report.items.append(DiagnosticItem("backups", DiagnosticStatus.CRITICAL, str(exc)))

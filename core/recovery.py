"""Guarded recovery operations for VASIKO itself."""
from __future__ import annotations

import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .backup_manager import BackupError, BackupManager


SAFE_RECOVERY_ACTIONS = frozenset({
    "retry_safe_operation", "restart_workflow", "disable_broken_integration",
    "switch_to_fallback", "cleanup_temp_files", "create_repair_plan",
})


@dataclass(frozen=True)
class RecoveryPlan:
    action: str
    allowed: bool
    requires_approval: bool
    reversible: bool
    reason: str


@dataclass(frozen=True)
class RecoveryResult:
    status: str
    message: str
    pre_restore_snapshot: str = ""
    restored_files: int = 0


class RecoveryManager:
    def __init__(self, backup_root: str | Path = "backups/vasiko") -> None:
        self.backup_root = Path(backup_root)

    def plan(self, action: str) -> RecoveryPlan:
        normalized = (action or "").strip().lower()
        if normalized in SAFE_RECOVERY_ACTIONS:
            return RecoveryPlan(normalized, True, False, True, "Разрешённое обратимое действие без внешнего эффекта")
        if normalized in {"restore_verified_backup", "restore_full_system", "delete_data", "change_permissions", "replace_credentials"}:
            return RecoveryPlan(normalized, False, True, False, "Опасное действие требует явного approval пользователя")
        return RecoveryPlan(normalized, False, True, False, "Неизвестное действие заблокировано")

    @staticmethod
    def _safe_member(member: tarfile.TarInfo, destination: Path) -> bool:
        target = (destination / PurePosixPath(member.name)).resolve()
        return target == destination.resolve() or destination.resolve() in target.parents

    def restore_verified_backup(self, archive: str | Path, destination: str | Path, approved: bool = False) -> RecoveryResult:
        archive = Path(archive)
        destination = Path(destination).resolve()
        verifier = BackupManager(destination, self.backup_root)
        try:
            manifest = verifier.verify(archive)
        except BackupError as exc:
            return RecoveryResult("blocked", f"Резервная копия не прошла проверку: {exc}")

        destination.mkdir(parents=True, exist_ok=True)
        pre_snapshot = verifier.create_snapshot("pre-restore")
        if not approved:
            return RecoveryResult("awaiting_approval", "Restore подготовлен и ожидает approval", str(pre_snapshot))

        restored = 0
        try:
            with tarfile.open(archive, "r:gz") as bundle:
                members = bundle.getmembers()
                if any(not self._safe_member(member, destination) for member in members):
                    return RecoveryResult("blocked", "Архив содержит небезопасный путь", str(pre_snapshot))
                bundle.extractall(destination, filter="data")
                restored = len(members)
        except (OSError, tarfile.TarError) as exc:
            return RecoveryResult("failed", f"Восстановление не выполнено: {exc}", str(pre_snapshot))
        return RecoveryResult("restored", f"Восстановлено по manifest {manifest.backup_id}", str(pre_snapshot), restored)

"""Safe local registry for VASIKO modules."""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ModuleRegistryError(ValueError):
    pass


class ModuleStatus(str, Enum):
    IDEA = "idea"
    DESCRIPTION = "description"
    MANIFEST = "manifest"
    DRAFT = "draft"
    TEST_ENVIRONMENT = "test_environment"
    QA = "qa"
    APPROVAL = "approval"
    ACTIVATION = "activation"
    MONITORING = "monitoring"
    UPGRADE = "upgrade"
    ROLLED_BACK = "rolled_back"


class ActivationStatus(str, Enum):
    INACTIVE = "inactive"
    PENDING = "pending"
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"


class ModuleTestStatus(str, Enum):
    NOT_RUN = "not_run"
    RUNNING = "running"
    FAILED = "failed"
    PASSED = "passed"


MODULE_ID = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
FORBIDDEN_PERMISSIONS = frozenset({
    "read_secrets", "change_own_constraints", "grant_self_permissions",
    "pay_without_approval", "publish_without_approval", "change_workspace_without_backup",
})
TRANSITIONS: dict[ModuleStatus, frozenset[ModuleStatus]] = {
    ModuleStatus.MANIFEST: frozenset({ModuleStatus.DRAFT}),
    ModuleStatus.DRAFT: frozenset({ModuleStatus.TEST_ENVIRONMENT}),
    ModuleStatus.TEST_ENVIRONMENT: frozenset({ModuleStatus.QA}),
    ModuleStatus.QA: frozenset({ModuleStatus.APPROVAL, ModuleStatus.DRAFT}),
    ModuleStatus.APPROVAL: frozenset({ModuleStatus.ACTIVATION, ModuleStatus.DRAFT}),
    ModuleStatus.ACTIVATION: frozenset({ModuleStatus.MONITORING}),
    ModuleStatus.MONITORING: frozenset({ModuleStatus.UPGRADE, ModuleStatus.ROLLED_BACK}),
    ModuleStatus.UPGRADE: frozenset({ModuleStatus.TEST_ENVIRONMENT}),
    ModuleStatus.ROLLED_BACK: frozenset({ModuleStatus.DRAFT}),
    ModuleStatus.IDEA: frozenset({ModuleStatus.DESCRIPTION}),
    ModuleStatus.DESCRIPTION: frozenset({ModuleStatus.MANIFEST}),
}


@dataclass
class ModuleManifest:
    module_id: str
    name: str
    version: str
    purpose: str
    status: ModuleStatus = ModuleStatus.IDEA
    required_skills: list[str] = field(default_factory=list)
    allowed_agents: list[str] = field(default_factory=list)
    required_integrations: list[str] = field(default_factory=list)
    input_contracts: list[str] = field(default_factory=list)
    output_contracts: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    budget_limits: dict[str, Any] = field(default_factory=dict)
    test_status: ModuleTestStatus = ModuleTestStatus.NOT_RUN
    activation_status: ActivationStatus = ActivationStatus.INACTIVE
    rollback_version: str = ""
    approval_id: str = ""

    def validate(self) -> None:
        if not MODULE_ID.fullmatch(self.module_id or ""):
            raise ModuleRegistryError("module_id должен быть snake_case длиной 2–64 символа")
        for field_name in ("name", "version", "purpose"):
            if not str(getattr(self, field_name)).strip():
                raise ModuleRegistryError(f"Поле manifest обязательно: {field_name}")
        forbidden = FORBIDDEN_PERMISSIONS.intersection(self.permissions)
        if forbidden:
            raise ModuleRegistryError(f"Запрещённые permissions: {', '.join(sorted(forbidden))}")
        if self.activation_status is not ActivationStatus.INACTIVE:
            raise ModuleRegistryError("Новый manifest не может быть активирован напрямую")


class ModuleRegistry:
    def __init__(self, root: str | Path = "modules/registry") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, module_id: str) -> Path:
        if not MODULE_ID.fullmatch(module_id or ""):
            raise ModuleRegistryError("Некорректный module_id")
        return self.root / f"{module_id}.json"

    @staticmethod
    def _serialize(manifest: ModuleManifest) -> dict[str, Any]:
        data = asdict(manifest)
        data["status"] = manifest.status.value
        data["test_status"] = manifest.test_status.value
        data["activation_status"] = manifest.activation_status.value
        return data

    @staticmethod
    def _deserialize(data: dict[str, Any]) -> ModuleManifest:
        data = dict(data)
        data["status"] = ModuleStatus(data["status"])
        data["test_status"] = ModuleTestStatus(data["test_status"])
        data["activation_status"] = ActivationStatus(data["activation_status"])
        return ModuleManifest(**data)

    def register(self, manifest: ModuleManifest) -> ModuleManifest:
        manifest.validate()
        path = self._path(manifest.module_id)
        if path.exists():
            raise ModuleRegistryError(f"Модуль уже зарегистрирован: {manifest.module_id}")
        manifest.status = ModuleStatus.MANIFEST
        manifest.activation_status = ActivationStatus.INACTIVE
        path.write_text(json.dumps(self._serialize(manifest), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return manifest

    def get(self, module_id: str) -> ModuleManifest | None:
        path = self._path(module_id)
        if not path.exists():
            return None
        return self._deserialize(json.loads(path.read_text(encoding="utf-8")))

    def list(self) -> list[ModuleManifest]:
        return [self._deserialize(json.loads(path.read_text(encoding="utf-8"))) for path in sorted(self.root.glob("*.json"))]

    def set_test_status(self, module_id: str, status: ModuleTestStatus) -> ModuleManifest:
        manifest = self._required(module_id)
        manifest.test_status = status
        self._save(manifest)
        return manifest

    def transition(self, module_id: str, target: ModuleStatus, approval_id: str = "") -> ModuleManifest:
        manifest = self._required(module_id)
        if target not in TRANSITIONS[manifest.status]:
            raise ModuleRegistryError(f"Переход {manifest.status.value} → {target.value} запрещён")
        if target is ModuleStatus.QA and manifest.test_status is not ModuleTestStatus.PASSED:
            raise ModuleRegistryError("Модуль нельзя передать в QA до успешного test_status=passed")
        if target is ModuleStatus.APPROVAL and manifest.test_status is not ModuleTestStatus.PASSED:
            raise ModuleRegistryError("Approval невозможен без успешных тестов")
        if target is ModuleStatus.ACTIVATION:
            if manifest.test_status is not ModuleTestStatus.PASSED:
                raise ModuleRegistryError("Активация невозможна без успешных тестов")
            if not approval_id.strip():
                raise ModuleRegistryError("Активация требует approval_id")
            manifest.approval_id = approval_id
            manifest.activation_status = ActivationStatus.ACTIVE
        if target is ModuleStatus.ROLLED_BACK:
            manifest.activation_status = ActivationStatus.ROLLED_BACK
        manifest.status = target
        self._save(manifest)
        return manifest

    def active(self) -> list[ModuleManifest]:
        return [manifest for manifest in self.list() if manifest.activation_status is ActivationStatus.ACTIVE]

    def _required(self, module_id: str) -> ModuleManifest:
        manifest = self.get(module_id)
        if manifest is None:
            raise ModuleRegistryError(f"Модуль не найден: {module_id}")
        return manifest

    def _save(self, manifest: ModuleManifest) -> None:
        manifest.validate() if manifest.activation_status is ActivationStatus.INACTIVE else None
        self._path(manifest.module_id).write_text(
            json.dumps(self._serialize(manifest), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

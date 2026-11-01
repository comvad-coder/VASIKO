"""Local connector registry. It stores references, never credentials."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from integrations.credentials_policy.policy import CredentialPolicyError, validate_credential_reference, validate_no_secrets


class ConnectorRegistryError(ValueError):
    pass


class ConnectorStatus(str, Enum):
    STUBBED = "stubbed"
    DISABLED = "disabled"
    NOT_CONNECTED = "not_connected"
    CONNECTED = "connected"


CONNECTOR_ID = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


@dataclass
class ConnectorManifest:
    integration_id: str
    name: str
    provider: str
    category: str
    version: str = "0.1.0"
    status: ConnectorStatus = ConnectorStatus.STUBBED
    required_scopes: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    credential_ref: str = ""
    approval_required: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not CONNECTOR_ID.fullmatch(self.integration_id or ""):
            raise ConnectorRegistryError("integration_id должен быть snake_case длиной 2–64 символа")
        for name in ("name", "provider", "category"):
            if not str(getattr(self, name)).strip():
                raise ConnectorRegistryError(f"Поле connector manifest обязательно: {name}")
        try:
            validate_no_secrets(asdict(self))
            if self.credential_ref:
                validate_credential_reference(self.credential_ref)
        except CredentialPolicyError as exc:
            raise ConnectorRegistryError(str(exc)) from exc


class ConnectorRegistry:
    def __init__(self, root: str | Path = "integrations/registry/manifests") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, integration_id: str) -> Path:
        if not CONNECTOR_ID.fullmatch(integration_id or ""):
            raise ConnectorRegistryError("Некорректный integration_id")
        return self.root / f"{integration_id}.json"

    @staticmethod
    def _serialize(manifest: ConnectorManifest) -> dict[str, Any]:
        data = asdict(manifest)
        data["status"] = manifest.status.value
        return data

    @staticmethod
    def _deserialize(data: dict[str, Any]) -> ConnectorManifest:
        data = dict(data)
        data["status"] = ConnectorStatus(data["status"])
        return ConnectorManifest(**data)

    def register(self, manifest: ConnectorManifest) -> ConnectorManifest:
        manifest.validate()
        path = self._path(manifest.integration_id)
        if path.exists():
            raise ConnectorRegistryError(f"Интеграция уже зарегистрирована: {manifest.integration_id}")
        manifest.status = ConnectorStatus.STUBBED
        path.write_text(json.dumps(self._serialize(manifest), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return manifest

    def get(self, integration_id: str) -> ConnectorManifest | None:
        path = self._path(integration_id)
        return self._deserialize(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else None

    def list(self) -> list[ConnectorManifest]:
        return [self._deserialize(json.loads(path.read_text(encoding="utf-8"))) for path in sorted(self.root.glob("*.json"))]

    def set_status(self, integration_id: str, status: ConnectorStatus, approval_id: str = "") -> ConnectorManifest:
        manifest = self.get(integration_id)
        if manifest is None:
            raise ConnectorRegistryError(f"Интеграция не найдена: {integration_id}")
        if status is ConnectorStatus.CONNECTED and (manifest.approval_required and not approval_id.strip()):
            raise ConnectorRegistryError("Подключение integration требует approval_id")
        manifest.status = status
        self._path(integration_id).write_text(json.dumps(self._serialize(manifest), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return manifest

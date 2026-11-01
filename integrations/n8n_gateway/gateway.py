"""n8n gateway boundary. It never makes HTTP calls in Block 6."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from integrations.credentials_policy.policy import CredentialPolicyError, safe_log_payload, validate_no_secrets


class N8nGatewayError(ValueError):
    pass


WORKFLOW_ID = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")


@dataclass
class WorkflowManifest:
    workflow_id: str
    name: str
    purpose: str
    required_integrations: list[str] = field(default_factory=list)
    external_action: bool = True
    status: str = "stubbed"

    def validate(self) -> None:
        if not WORKFLOW_ID.fullmatch(self.workflow_id or ""):
            raise N8nGatewayError("workflow_id должен быть snake_case или kebab-case")
        if not self.name.strip() or not self.purpose.strip():
            raise N8nGatewayError("name и purpose обязательны")


@dataclass(frozen=True)
class WorkflowRun:
    workflow_id: str
    task_id: str
    status: str
    message: str
    approval_id: str = ""
    safe_payload_keys: tuple[str, ...] = ()


class N8nWorkflowRegistry:
    def __init__(self, root: str | Path = "n8n/workflows") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def register(self, workflow: WorkflowManifest) -> WorkflowManifest:
        workflow.validate()
        path = self.root / f"{workflow.workflow_id}.json"
        if path.exists():
            raise N8nGatewayError(f"Workflow уже зарегистрирован: {workflow.workflow_id}")
        path.write_text(json.dumps(workflow.__dict__, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return workflow

    def get(self, workflow_id: str) -> WorkflowManifest | None:
        path = self.root / f"{workflow_id}.json"
        if not path.exists():
            return None
        return WorkflowManifest(**json.loads(path.read_text(encoding="utf-8")))


class N8nGateway:
    def __init__(self, workflows: N8nWorkflowRegistry) -> None:
        self.workflows = workflows
        self.audit_log: list[dict[str, Any]] = []

    def dispatch(self, workflow_id: str, task_id: str, payload: dict[str, Any], approval_id: str = "") -> WorkflowRun:
        workflow = self.workflows.get(workflow_id)
        if workflow is None:
            raise N8nGatewayError(f"Workflow не найден: {workflow_id}")
        try:
            validate_no_secrets(payload)
            safe_payload = safe_log_payload(payload)
        except CredentialPolicyError as exc:
            raise N8nGatewayError(str(exc)) from exc
        if workflow.external_action and not approval_id.strip():
            return WorkflowRun(workflow_id, task_id, "awaiting_approval", "Внешний workflow ожидает approval", safe_payload_keys=tuple(sorted(safe_payload)))
        result = WorkflowRun(workflow_id, task_id, "stubbed", "n8n gateway не подключён; сетевой вызов не выполнялся", approval_id, tuple(sorted(safe_payload)))
        self.audit_log.append({"workflow_id": workflow_id, "task_id": task_id, "status": result.status, "payload_keys": list(result.safe_payload_keys)})
        return result

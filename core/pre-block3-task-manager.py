"""Local JSON task manager for VASIKO Block 3.

This is a replaceable adapter behind the Core task boundary. It deliberately
stores no credentials and performs no external actions.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import asdict
from pathlib import Path

from .domain import EntityRef, EntityType, TaskSpec, TaskStatus, utc_now

TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.NEW: frozenset({TaskStatus.PLANNED, TaskStatus.BLOCKED, TaskStatus.CANCELLED}),
    TaskStatus.PLANNED: frozenset({TaskStatus.AWAITING_APPROVAL, TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.CANCELLED}),
    TaskStatus.AWAITING_APPROVAL: frozenset({TaskStatus.PLANNED, TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.CANCELLED}),
    TaskStatus.RUNNING: frozenset({TaskStatus.CHECKPOINT, TaskStatus.QA, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.BLOCKED}),
    TaskStatus.CHECKPOINT: frozenset({TaskStatus.RUNNING, TaskStatus.QA, TaskStatus.FAILED, TaskStatus.CANCELLED}),
    TaskStatus.QA: frozenset({TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.ROLLED_BACK}),
    TaskStatus.FAILED: frozenset({TaskStatus.PLANNED, TaskStatus.RUNNING, TaskStatus.ROLLED_BACK}),
    TaskStatus.ROLLED_BACK: frozenset({TaskStatus.PLANNED}),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
    TaskStatus.BLOCKED: frozenset({TaskStatus.PLANNED, TaskStatus.CANCELLED}),
}


def _validate_task_id(task_id: str) -> str:
    if not TASK_ID_RE.fullmatch(task_id or ""):
        raise ValueError("task_id должен содержать 1–64 символа: буквы, цифры, '.', '_' или '-'")
    return task_id


def _to_json(task: TaskSpec) -> dict:
    data = asdict(task)
    data["status"] = task.status.value
    for key in ("project",):
        ref = data[key]
        if ref:
            data[key] = {"entity_type": ref["entity_type"].value, "entity_id": ref["entity_id"]}
    for key in ("products", "workspaces"):
        data[key] = [{"entity_type": item["entity_type"].value, "entity_id": item["entity_id"]} for item in data[key]]
    return data


def _from_json(data: dict) -> TaskSpec:
    def ref(value: dict | None) -> EntityRef | None:
        return EntityRef(EntityType(value["entity_type"]), value["entity_id"]) if value else None
    return TaskSpec(
        task_id=data["task_id"], objective=data["objective"], status=TaskStatus(data["status"]),
        project=ref(data.get("project")),
        products=[ref(item) for item in data.get("products", []) if ref(item)],
        workspaces=[ref(item) for item in data.get("workspaces", []) if ref(item)],
        plan=data.get("plan", ""), checkpoints=data.get("checkpoints", []),
        artifacts=data.get("artifacts", []), errors=data.get("errors", []), next_step=data.get("next_step", ""),
        created_at=data.get("created_at", utc_now()), updated_at=data.get("updated_at", utc_now()),
    )


class LocalTaskManager:
    def __init__(self, root: str | Path = "tasks/records") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, task_id: str) -> Path:
        return self.root / f"{_validate_task_id(task_id)}.json"

    def create(self, task: TaskSpec) -> TaskSpec:
        _validate_task_id(task.task_id)
        if self._path(task.task_id).exists():
            raise FileExistsError(f"Задача уже существует: {task.task_id}")
        self.save(task)
        return task

    def save(self, task: TaskSpec) -> None:
        target = self._path(task.task_id)
        payload = json.dumps(_to_json(task), ensure_ascii=False, indent=2) + "\n"
        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, target)

    def get(self, task_id: str) -> TaskSpec | None:
        target = self._path(task_id)
        if not target.exists():
            return None
        return _from_json(json.loads(target.read_text(encoding="utf-8")))

    def list(self) -> list[TaskSpec]:
        return [self.get(path.stem) for path in sorted(self.root.glob("*.json")) if self.get(path.stem)]

    def transition(self, task_id: str, target: TaskStatus) -> TaskSpec:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"Задача не найдена: {task_id}")
        if target not in TRANSITIONS[task.status]:
            raise ValueError(f"Переход {task.status.value} → {target.value} запрещён")
        task.status = target
        task.updated_at = utc_now()
        self.save(task)
        return task

    def checkpoint(self, task_id: str, label: str) -> TaskSpec:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"Задача не найдена: {task_id}")
        if task.status not in {TaskStatus.RUNNING, TaskStatus.CHECKPOINT}:
            raise ValueError("Checkpoint разрешён только для running или checkpoint задачи")
        if not label.strip():
            raise ValueError("Название checkpoint обязательно")
        task.checkpoints.append(label.strip())
        task.status = TaskStatus.CHECKPOINT
        task.updated_at = utc_now()
        self.save(task)
        return task

    def resume(self, task_id: str) -> TaskSpec:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"Задача не найдена: {task_id}")
        if not task.checkpoints:
            raise ValueError("Нельзя продолжить задачу без сохранённого checkpoint")
        if task.status not in {TaskStatus.CHECKPOINT, TaskStatus.FAILED, TaskStatus.BLOCKED}:
            raise ValueError("Продолжение возможно из checkpoint, failed или blocked")
        task.status = TaskStatus.RUNNING
        task.next_step = f"Продолжить с checkpoint: {task.checkpoints[-1]}"
        task.updated_at = utc_now()
        self.save(task)
        return task

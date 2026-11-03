"""VASIKO Gradio Admin with local, safe project workspace import.

The Admin UI performs only local filesystem work in this block. It does not call
external APIs, publish content, send messages, process payments, or use AI.
"""
from __future__ import annotations

import json
import os
import re
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import gradio as gr
except ImportError:  # pragma: no cover - gives a useful CLI error when launched without deps
    gr = None

from modules.project_workspace.workspace_manager import WorkspaceError, WorkspaceManager

BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / "runtime"
BACKUP_DIR = RUNTIME_DIR / "backups"
WORKSPACES_DIR = PROJECT_ROOT / "workspaces" / "projects"

TASK_STATUSES = (
    "new", "planned", "awaiting_approval", "running", "checkpoint", "qa",
    "completed", "failed", "cancelled", "blocked", "rolled_back",
)


@dataclass
class Task:
    task_id: str
    title: str
    objective: str
    product_url: str = ""
    zip_name: str = ""
    zip_path: str = ""
    product_id: str = "external_product"
    workspace_id: str = ""
    workspace_status: str = "not_imported"
    workspace_report: str = ""
    status: str = "new"
    plan: str = (
        "Проверить входы → сохранить оригинал ZIP → безопасно распаковать workspace "
        "→ создать import report → подготовить следующий внутренний шаг."
    )
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdminStore:
    """Local Admin adapter for Core and project workspace services."""

    def __init__(self, workspace_manager: WorkspaceManager | None = None) -> None:
        self.tasks: dict[str, Task] = {}
        self.audit: list[dict[str, str]] = []
        self.approvals: list[dict[str, str]] = []
        self.workspace_manager = workspace_manager or WorkspaceManager(WORKSPACES_DIR)

    def _log(self, action: str, details: str) -> None:
        self.audit.insert(0, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details,
        })

    @staticmethod
    def _product_id(title: str, objective: str, zip_path: str | None) -> str:
        source = " ".join(item for item in (title, objective, Path(zip_path).name if zip_path else "") if item).lower()
        return "palm" if "palm" in source else "external_product"

    @staticmethod
    def _workspace_id(product_id: str, task_id: str, zip_path: str | None) -> str:
        if product_id == "palm":
            return "palm-site"
        stem = Path(zip_path).stem.lower() if zip_path else ""
        slug = re.sub(r"[^a-z0-9_-]+", "-", stem).strip("-_")
        if not slug or not slug[0].isalpha():
            slug = f"workspace-{task_id.removeprefix('task-')}"
        return slug[:64]

    def create_task(self, title: str, objective: str, product_url: str = "", zip_path: str | None = None) -> Task:
        title = (title or "").strip()
        objective = (objective or "").strip()
        if not title:
            raise ValueError("Название задачи обязательно")
        if not objective:
            raise ValueError("Цель задачи обязательна")
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        product_id = self._product_id(title, objective, zip_path)
        task = Task(
            task_id=task_id,
            title=title,
            objective=objective,
            product_url=(product_url or "").strip(),
            zip_name=Path(zip_path).name if zip_path else "",
            zip_path=str(zip_path or ""),
            product_id=product_id,
            workspace_id=self._workspace_id(product_id, task_id, zip_path),
        )
        self.tasks[task.task_id] = task
        self._log("task.created", task.task_id)
        if task.zip_name:
            self._log("workspace.upload_registered", f"{task.task_id}:{task.zip_name}")
        return task

    def update_status(self, task_id: str, status: str) -> Task:
        if task_id not in self.tasks:
            raise ValueError("Задача не найдена")
        if status not in TASK_STATUSES:
            raise ValueError("Недопустимый статус")
        task = self.tasks[task_id]
        task.status = status
        task.updated_at = datetime.now(timezone.utc).isoformat()
        self._log(f"task.{status}", task_id)
        return task

    def approve(self, task_id: str) -> Task:
        task = self.update_status(task_id, "planned")
        self.approvals.insert(0, {"task_id": task_id, "decision": "approved", "timestamp": task.updated_at})
        self._log("approval.granted", task_id)
        return task

    def start(self, task_id: str) -> Task:
        if task_id not in self.tasks:
            raise ValueError("Задача не найдена")
        task = self.tasks[task_id]
        if task.zip_path:
            try:
                manifest = self.workspace_manager.import_zip(
                    task.zip_path,
                    task.workspace_id,
                    task.product_id,
                    allow_metadata_stub=True,
                )
            except (WorkspaceError, OSError) as exc:
                task.status = "blocked"
                task.workspace_status = "import_failed"
                task.workspace_report = str(exc)
                task.updated_at = datetime.now(timezone.utc).isoformat()
                self._log("workspace.import_failed", f"{task.task_id}:{exc}")
                raise
            task.workspace_status = manifest.status
            task.workspace_report = (
                f"{manifest.file_count} files; {manifest.uncompressed_bytes} bytes; "
                f"stacks={','.join(manifest.detected_stacks) or 'unknown'}"
            )
            task.status = "running"
            task.updated_at = datetime.now(timezone.utc).isoformat()
            self._log("workspace.imported", f"{task.task_id}:{task.workspace_id}")
            self._log("task.running", task.task_id)
            return task
        return self.update_status(task_id, "running")

    def rows(self) -> list[list[str]]:
        return [
            [
                t.task_id, t.title, t.status, t.product_url, t.zip_name,
                t.workspace_id, t.workspace_status, t.workspace_report, t.updated_at,
            ]
            for t in self.tasks.values()
        ]

    def snapshot(self) -> dict[str, Any]:
        return {"tasks": [asdict(t) for t in self.tasks.values()], "approvals": self.approvals, "audit": self.audit}

    def backup(self) -> Path:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = BACKUP_DIR / f"admin-snapshot-{stamp}.json"
        target.write_text(json.dumps(self.snapshot(), ensure_ascii=False, indent=2), encoding="utf-8")
        self._log("backup.created", target.name)
        return target

    def diagnostics(self) -> dict[str, str]:
        checks = {
            "admin_process": "healthy",
            "task_store": "healthy",
            "workspace_import": "ready",
            "backup_directory": "healthy" if BACKUP_DIR.exists() else "warning",
            "external_integrations": "stubbed",
            "n8n_gateway": "not_connected",
        }
        self._log("diagnostics.run", json.dumps(checks, ensure_ascii=False))
        return checks


STORE = AdminStore()


def _selected_task(task_id: str) -> str:
    task_id = (task_id or "").strip()
    if not task_id:
        raise ValueError("Укажите task_id")
    return task_id


def create_task_action(title: str, objective: str, url: str, zip_file: Any):
    try:
        path = getattr(zip_file, "name", None) or (zip_file if isinstance(zip_file, str) else None)
        task = STORE.create_task(title, objective, url, path)
        message = f"Создана задача `{task.task_id}` со статусом `{task.status}`. ZIP зарегистрирован; импорт будет выполнен кнопкой «Запустить»."
        return STORE.rows(), task.task_id, message
    except (ValueError, TypeError) as exc:
        return STORE.rows(), "", f"Ошибка: {exc}"


def plan_action(task_id: str):
    try:
        task = STORE.tasks[_selected_task(task_id)]
        return task.plan, f"План доступен для `{task.task_id}`. Внешние действия не выполняются."
    except (KeyError, ValueError) as exc:
        return "", f"Ошибка: {exc}"


def approve_action(task_id: str):
    try:
        task = STORE.approve(_selected_task(task_id))
        return STORE.rows(), f"Подтвержден безопасный внутренний план `{task.task_id}`; статус: `{task.status}`."
    except (KeyError, ValueError) as exc:
        return STORE.rows(), f"Ошибка: {exc}"


def start_action(task_id: str):
    try:
        task = STORE.start(_selected_task(task_id))
        if task.workspace_status == "imported":
            return STORE.rows(), f"ZIP импортирован в `{task.workspace_id}`: {task.workspace_report}. Реальные интеграции не вызываются."
        return STORE.rows(), f"Запущена stub-задача `{task.task_id}`. Реальные интеграции не вызываются."
    except (KeyError, ValueError, WorkspaceError, OSError) as exc:
        return STORE.rows(), f"Ошибка запуска/import: {exc}"


def stop_action(task_id: str):
    try:
        task = STORE.update_status(_selected_task(task_id), "cancelled")
        return STORE.rows(), f"Задача `{task.task_id}` остановлена."
    except (KeyError, ValueError) as exc:
        return STORE.rows(), f"Ошибка: {exc}"


def backup_action():
    try:
        path = STORE.backup()
        return f"Резервная копия создана локально: `{path.name}`. Секреты не включаются."
    except OSError as exc:
        return f"Ошибка backup: {exc}"


def diagnostics_action():
    checks = STORE.diagnostics()
    return "\n".join(f"- **{key}**: `{value}`" for key, value in checks.items())


def audit_action():
    return [[item["timestamp"], item["action"], item["details"]] for item in STORE.audit]


def placeholder(title: str) -> str:
    return f"**{title}** — рабочая заглушка. Назначение раздела будет реализовано отдельным модулем после проверки предыдущего блока."


def build_app():
    if gr is None:
        raise RuntimeError("Gradio не установлен. Выполните: pip install -r requirements.txt")
    with gr.Blocks(title="VASIKO Admin") as app:
        gr.Markdown("# VASIKO Admin\nZIP импортируется локально в isolated workspace. Внешние действия пока заменены заглушками.")
        with gr.Tab("Dashboard"):
            gr.Markdown("Центральный обзор состояния ВАСИКО и быстрых безопасных действий.")
            with gr.Row():
                diag_btn = gr.Button("Запустить диагностику")
                backup_btn = gr.Button("Создать резервную копию")
            diag_out = gr.Markdown()
            backup_out = gr.Markdown()
            diag_btn.click(diagnostics_action, outputs=diag_out)
            backup_btn.click(backup_action, outputs=backup_out)
        with gr.Tab("Tasks"):
            gr.Markdown("### Создание и управление задачами")
            with gr.Row():
                title = gr.Textbox(label="Название задачи", value="")
                objective = gr.Textbox(label="Цель", value="")
            url = gr.Textbox(label="URL продукта", placeholder="https://example.com")
            zip_file = gr.File(label="ZIP проекта (оригинал сохранится, импорт при запуске)", file_types=[".zip"], type="filepath")
            create_btn = gr.Button("Создать задачу", variant="primary")
            task_table = gr.Dataframe(
                headers=["task_id", "title", "status", "product_url", "zip_name", "workspace_id", "workspace_status", "workspace_report", "updated_at"],
                label="Задачи", value=STORE.rows(), interactive=False,
            )
            selected = gr.Textbox(label="task_id")
            with gr.Row():
                plan_btn = gr.Button("Показать план")
                approve_btn = gr.Button("Подтвердить план")
                start_btn = gr.Button("Запустить")
                stop_btn = gr.Button("Остановить")
            plan_out = gr.Markdown()
            task_out = gr.Markdown()
            create_btn.click(create_task_action, [title, objective, url, zip_file], [task_table, selected, task_out])
            plan_btn.click(plan_action, selected, [plan_out, task_out])
            approve_btn.click(approve_action, selected, [task_table, task_out])
            start_btn.click(start_action, selected, [task_table, task_out])
            stop_btn.click(stop_action, selected, [task_table, task_out])
        for name in ("Products", "Workspaces", "Agents", "Skills", "Modules", "Integrations", "n8n", "Promotion", "Content", "Video", "Publications", "Analytics", "Approvals", "Memory", "Backups", "Diagnostics", "Recovery", "Settings"):
            with gr.Tab(name):
                gr.Markdown(placeholder(name))
        with gr.Tab("Action Log"):
            log_table = gr.Dataframe(headers=["timestamp", "action", "details"], value=[], interactive=False)
            refresh = gr.Button("Обновить журнал")
            refresh.click(audit_action, outputs=log_table)
    return app


if __name__ == "__main__":
    build_app().launch(server_name=os.getenv("VASIKO_HOST", "127.0.0.1"), server_port=int(os.getenv("VASIKO_PORT", "7860")))

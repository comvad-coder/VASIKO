"""VASIKO Gradio Admin — Block 1 scaffold.

This block intentionally uses an in-memory store and local JSON backups only.
It does not call external APIs, publish content, send messages, process payments,
or unpack uploaded projects.
"""
from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import gradio as gr
except ImportError:  # pragma: no cover - gives a useful CLI error when launched without deps
    gr = None

BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / "runtime"
BACKUP_DIR = RUNTIME_DIR / "backups"

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
    status: str = "new"
    plan: str = "Черновой план: уточнить цель, проверить входы, подготовить безопасный следующий шаг."
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdminStore:
    """Small local substitute for future Core services.

    The boundary is deliberate: later blocks can replace this class with Core
    Task Manager, Audit Log, Approval and Backup services without changing the UI.
    """

    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}
        self.audit: list[dict[str, str]] = []
        self.approvals: list[dict[str, str]] = []

    def _log(self, action: str, details: str) -> None:
        self.audit.insert(0, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details,
        })

    def create_task(self, title: str, objective: str, product_url: str = "", zip_path: str | None = None) -> Task:
        title = (title or "").strip()
        objective = (objective or "").strip()
        if not title:
            raise ValueError("Название задачи обязательно")
        if not objective:
            raise ValueError("Цель задачи обязательна")
        task = Task(
            task_id=f"task-{uuid.uuid4().hex[:8]}",
            title=title,
            objective=objective,
            product_url=(product_url or "").strip(),
            zip_name=Path(zip_path).name if zip_path else "",
        )
        self.tasks[task.task_id] = task
        self._log("task.created", task.task_id)
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

    def rows(self) -> list[list[str]]:
        return [[t.task_id, t.title, t.status, t.product_url, t.zip_name, t.updated_at] for t in self.tasks.values()]

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
        return STORE.rows(), task.task_id, f"Создана задача `{task.task_id}` со статусом `{task.status}`."
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
        task = STORE.update_status(_selected_task(task_id), "running")
        return STORE.rows(), f"Запущена stub-задача `{task.task_id}`. Реальные интеграции не вызываются."
    except (KeyError, ValueError) as exc:
        return STORE.rows(), f"Ошибка: {exc}"


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
    return f"**{title}** — рабочая заглушка первого блока. Назначение раздела будет реализовано отдельным модулем после подтверждения предыдущего блока."


def build_app():
    if gr is None:
        raise RuntimeError("Gradio не установлен. Выполните: pip install -r requirements.txt")
    with gr.Blocks(title="VASIKO Admin") as app:
        gr.Markdown("# VASIKO Admin\nАдминистративная панель ВАСИКО. Внешние действия пока заменены заглушками.")
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
            zip_file = gr.File(label="ZIP проекта (регистрация входа, без распаковки)", file_types=[".zip"], type="filepath")
            create_btn = gr.Button("Создать задачу", variant="primary")
            task_table = gr.Dataframe(headers=["task_id", "title", "status", "product_url", "zip_name", "updated_at"], label="Задачи", value=STORE.rows(), interactive=False)
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

from pathlib import Path
import zipfile

import pytest

from admin.gradio_admin.app import AdminStore, TASK_STATUSES
from modules.project_workspace.workspace_manager import WorkspaceManager


def test_task_lifecycle_and_audit():
    store = AdminStore()
    task = store.create_task("Demo", "Check the admin flow", "https://example.test", "/tmp/project.zip")
    assert task.status == "new"
    assert task.zip_name == "project.zip"

    store.approve(task.task_id)
    store.update_status(task.task_id, "running")
    store.update_status(task.task_id, "cancelled")

    assert store.tasks[task.task_id].status == "cancelled"
    assert [item["action"] for item in store.audit] == [
        "task.cancelled", "task.running", "approval.granted", "task.planned",
        "workspace.upload_registered", "task.created",
    ]


def test_required_fields_are_validated():
    store = AdminStore()
    with pytest.raises(ValueError, match="Название"):
        store.create_task("", "objective")
    with pytest.raises(ValueError, match="Цель"):
        store.create_task("title", "")


def test_backup_is_local_json(tmp_path, monkeypatch):
    import admin.gradio_admin.app as app

    monkeypatch.setattr(app, "BACKUP_DIR", Path(tmp_path))
    store = AdminStore()
    store.create_task("Backup", "Create a snapshot")
    target = store.backup()

    assert target.exists()
    assert target.suffix == ".json"
    assert "tasks" in target.read_text(encoding="utf-8")


def test_diagnostics_do_not_call_external_services():
    store = AdminStore()
    result = store.diagnostics()
    assert result["admin_process"] == "healthy"
    assert result["external_integrations"] == "stubbed"
    assert set(TASK_STATUSES) >= {"new", "running", "cancelled"}


def test_admin_start_imports_uploaded_palm_zip(tmp_path):
    archive = tmp_path / "palm-promotion.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("package.json", "{}")
        bundle.writestr("src/index.js", "console.log('palm')")

    store = AdminStore(WorkspaceManager(tmp_path / "workspaces"))
    task = store.create_task("Продвижение Palm", "Поиск клиентов", zip_path=str(archive))
    started = store.start(task.task_id)
    workspace = tmp_path / "workspaces" / "palm-site"

    assert started.status == "running"
    assert started.workspace_id == "palm-site"
    assert started.workspace_status == "imported"
    assert (workspace / "original" / archive.name).is_file()
    assert (workspace / "extracted" / "src" / "index.js").read_text() == "console.log('palm')"
    assert (workspace / "analysis" / "import-report.json").is_file()


def test_admin_start_blocks_secret_zip(tmp_path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(".env", "TOKEN=not-stored")

    store = AdminStore(WorkspaceManager(tmp_path / "workspaces"))
    task = store.create_task("Продвижение Palm", "Поиск клиентов", zip_path=str(archive))
    with pytest.raises(ValueError, match="секретный"):
        store.start(task.task_id)

    assert store.tasks[task.task_id].status == "blocked"
    assert store.tasks[task.task_id].workspace_status == "import_failed"

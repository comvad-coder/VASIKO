from pathlib import Path

import pytest

from admin.gradio_admin.app import AdminStore, TASK_STATUSES


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
        "task.cancelled", "task.running", "approval.granted", "task.planned", "task.created"
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

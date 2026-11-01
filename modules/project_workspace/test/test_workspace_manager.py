import io
import zipfile

import pytest

from modules.project_workspace.workspace_manager import WorkspaceError, WorkspaceManager, WorkspacePolicy


def make_zip(path, entries):
    with zipfile.ZipFile(path, "w") as bundle:
        for name, content in entries.items():
            bundle.writestr(name, content)


def test_import_creates_isolated_workspace_and_report(tmp_path):
    archive = tmp_path / "palm-site.zip"
    make_zip(archive, {"package.json": "{}", "src/index.js": "console.log(1)"})
    manager = WorkspaceManager(tmp_path / "workspaces")

    manifest = manager.import_zip(archive, "palm-site", "palm")
    workspace = tmp_path / "workspaces" / "palm-site"
    assert manifest.status == "imported"
    assert manifest.detected_stacks == ["node"]
    assert (workspace / "original" / "palm-site.zip").is_file()
    assert (workspace / "extracted" / "src" / "index.js").read_text() == "console.log(1)"
    assert (workspace / "analysis" / "import-report.json").is_file()

    backup = manager.create_change_backup("palm-site")
    assert (backup / "src" / "index.js").is_file()
    assert manager._read_manifest(workspace).backup_count == 1


def test_path_traversal_and_secret_file_are_rejected(tmp_path):
    traversal = tmp_path / "traversal.zip"
    make_zip(traversal, {"../escape.txt": "bad"})
    with pytest.raises(WorkspaceError, match="Небезопасный путь"):
        WorkspaceManager(tmp_path / "workspaces").import_zip(traversal, "bad-workspace")

    secret = tmp_path / "secret.zip"
    make_zip(secret, {".env": "TOKEN=not-stored"})
    with pytest.raises(WorkspaceError, match="секретный"):
        WorkspaceManager(tmp_path / "workspaces2").import_zip(secret, "secret-workspace")


def test_limits_and_duplicate_workspace_are_rejected(tmp_path):
    archive = tmp_path / "large.zip"
    make_zip(archive, {"package.json": "{}", "a.txt": "x" * 20})
    manager = WorkspaceManager(tmp_path / "workspaces", WorkspacePolicy(max_archive_bytes=1024, max_file_bytes=10))
    with pytest.raises(WorkspaceError, match="превышает"):
        manager.import_zip(archive, "large-workspace")

    small_manager = WorkspaceManager(tmp_path / "small")
    small = tmp_path / "small.zip"
    make_zip(small, {"README.md": "ok"})
    small_manager.import_zip(small, "demo")
    with pytest.raises(WorkspaceError, match="уже существует"):
        small_manager.import_zip(small, "demo")

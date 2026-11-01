import json

import pytest

from core.backup_manager import BackupError, BackupManager


def test_backup_creates_manifest_and_excludes_secrets(tmp_path):
    source = tmp_path / "source"
    (source / "core").mkdir(parents=True)
    (source / "core" / "domain.py").write_text("safe", encoding="utf-8")
    (source / ".env").write_text("SECRET=do-not-backup", encoding="utf-8")
    (source / "credentials.json").write_text("do-not-backup", encoding="utf-8")
    manager = BackupManager(source, tmp_path / "backups")

    archive = manager.create_snapshot("vasiko")
    manifest = manager.verify(archive)
    assert manifest.file_count == 1
    assert json.loads(archive.with_suffix(archive.suffix + ".manifest.json").read_text())["archive_sha256"]

    import tarfile
    with tarfile.open(archive, "r:gz") as bundle:
        names = bundle.getnames()
    assert names == ["core/domain.py"]


def test_backup_detects_tampering(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("safe", encoding="utf-8")
    manager = BackupManager(source, tmp_path / "backups")
    archive = manager.create_snapshot()
    archive.write_bytes(archive.read_bytes() + b"tamper")
    with pytest.raises(BackupError, match="SHA-256"):
        manager.verify(archive)

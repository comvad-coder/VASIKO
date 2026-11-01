from core.backup_manager import BackupManager
from core.recovery import RecoveryManager


def test_restore_requires_approval_and_creates_pre_restore_snapshot(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("version-1", encoding="utf-8")
    backup_root = tmp_path / "backups"
    archive = BackupManager(source, backup_root).create_snapshot()
    destination = tmp_path / "destination"
    manager = RecoveryManager(backup_root)

    pending = manager.restore_verified_backup(archive, destination, approved=False)
    assert pending.status == "awaiting_approval"
    assert pending.pre_restore_snapshot

    restored = manager.restore_verified_backup(archive, destination, approved=True)
    assert restored.status == "restored"
    assert (destination / "README.md").read_text(encoding="utf-8") == "version-1"


def test_recovery_plan_fails_closed():
    manager = RecoveryManager()
    assert manager.plan("cleanup_temp_files").allowed is True
    assert manager.plan("restore_full_system").requires_approval is True
    assert manager.plan("unknown").allowed is False

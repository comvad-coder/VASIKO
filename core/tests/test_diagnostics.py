from core.backup_manager import BackupManager
from core.diagnostics import DiagnosticStatus, SystemDiagnostics


def test_diagnostics_reports_stub_integrations_and_backup(tmp_path):
    for path in [tmp_path / "tasks" / "records", tmp_path / "memory"]:
        path.mkdir(parents=True, exist_ok=True)
    for path in [tmp_path / "core" / "domain.py", tmp_path / "admin" / "gradio_admin" / "app.py"]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")
    manager = BackupManager(tmp_path, tmp_path / "backups" / "vasiko")
    manager.create_snapshot()
    report = SystemDiagnostics(tmp_path, manager).run()
    assert report.overall_status is DiagnosticStatus.WARNING
    items = {item.component: item for item in report.items}
    assert items["backups"].status is DiagnosticStatus.HEALTHY
    assert items["n8n_gateway"].status is DiagnosticStatus.WARNING


def test_missing_core_is_critical(tmp_path):
    report = SystemDiagnostics(tmp_path).run()
    assert report.overall_status is DiagnosticStatus.CRITICAL

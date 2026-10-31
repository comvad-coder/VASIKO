from core.system_state import run_local_diagnostics


def test_local_diagnostics_are_explicit_about_stubs(tmp_path):
    state = run_local_diagnostics(tmp_path)
    assert state.overall_status == "healthy"
    statuses = {check.component: check.status for check in state.checks}
    assert statuses["core"] == "healthy"
    assert statuses["external_integrations"] == "stubbed"
    assert statuses["n8n_gateway"] == "not_connected"


def test_missing_runtime_is_warning(tmp_path):
    state = run_local_diagnostics(tmp_path / "missing")
    assert state.overall_status == "warning"

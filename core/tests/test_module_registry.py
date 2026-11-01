import pytest

from core.module_registry import (
    ActivationStatus,
    ModuleManifest,
    ModuleRegistry,
    ModuleRegistryError,
    ModuleStatus,
    ModuleTestStatus,
)


def manifest(module_id="demo_module"):
    return ModuleManifest(
        module_id=module_id, name="Demo Module", version="0.1.0", purpose="Test registry",
        required_skills=["planning"], allowed_agents=["planner"], permissions=["create_draft"],
        budget_limits={"max_cost": 0}, rollback_version="0.0.0",
    )


def test_register_is_inactive_until_tests_and_approval(tmp_path):
    registry = ModuleRegistry(tmp_path / "registry")
    item = registry.register(manifest())
    assert item.status is ModuleStatus.MANIFEST
    assert item.activation_status is ActivationStatus.INACTIVE
    assert registry.active() == []

    registry.transition("demo_module", ModuleStatus.DRAFT)
    registry.transition("demo_module", ModuleStatus.TEST_ENVIRONMENT)
    with pytest.raises(ModuleRegistryError, match="test_status"):
        registry.transition("demo_module", ModuleStatus.QA)

    registry.set_test_status("demo_module", ModuleTestStatus.PASSED)
    registry.transition("demo_module", ModuleStatus.QA)
    registry.transition("demo_module", ModuleStatus.APPROVAL)
    with pytest.raises(ModuleRegistryError, match="approval_id"):
        registry.transition("demo_module", ModuleStatus.ACTIVATION)
    activated = registry.transition("demo_module", ModuleStatus.ACTIVATION, "approval-1")
    assert activated.activation_status is ActivationStatus.ACTIVE
    assert registry.active()[0].module_id == "demo_module"


def test_forbidden_permissions_and_duplicate_are_rejected(tmp_path):
    registry = ModuleRegistry(tmp_path / "registry")
    with pytest.raises(ModuleRegistryError, match="Запрещённые"):
        registry.register(ModuleManifest("bad_module", "Bad", "1.0", "Bad", permissions=["read_secrets"]))
    registry.register(manifest())
    with pytest.raises(ModuleRegistryError, match="уже зарегистрирован"):
        registry.register(manifest())


def test_future_module_has_no_implicit_rights(tmp_path):
    registry = ModuleRegistry(tmp_path / "registry")
    future = manifest("voice_operator")
    registered = registry.register(future)
    assert registered.permissions == ["create_draft"]
    assert registered.activation_status is ActivationStatus.INACTIVE

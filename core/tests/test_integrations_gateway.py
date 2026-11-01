import pytest

from integrations.credentials_policy.policy import CredentialPolicyError, validate_credential_reference, validate_no_secrets
from integrations.n8n_gateway.gateway import N8nGateway, N8nGatewayError, N8nWorkflowRegistry, WorkflowManifest
from integrations.registry.connector_registry import ConnectorManifest, ConnectorRegistry, ConnectorRegistryError, ConnectorStatus


def test_connector_registry_stores_reference_not_secret(tmp_path):
    registry = ConnectorRegistry(tmp_path / "manifests")
    connector = registry.register(ConnectorManifest(
        "research_stub", "Research Stub", "example", "research", credential_ref="n8n.research.example",
    ))
    assert connector.status is ConnectorStatus.STUBBED
    with pytest.raises(ConnectorRegistryError, match="Секретное"):
        registry.register(ConnectorManifest("bad_connector", "Bad", "example", "ai", metadata={"api_key": "secret"}))
    with pytest.raises(ConnectorRegistryError, match="approval_id"):
        registry.set_status("research_stub", ConnectorStatus.CONNECTED)


def test_credentials_policy_blocks_secrets():
    assert validate_credential_reference("n8n.service.main") == "n8n.service.main"
    with pytest.raises(CredentialPolicyError):
        validate_credential_reference("password")
    with pytest.raises(CredentialPolicyError):
        validate_no_secrets({"normal": "Authorization bearer abcdefghijklmnop"})


def test_n8n_gateway_requires_approval_and_never_calls_network(tmp_path):
    workflows = N8nWorkflowRegistry(tmp_path / "workflows")
    workflows.register(WorkflowManifest("publish_stub", "Publish Stub", "Prepare publication", ["social_stub"]))
    gateway = N8nGateway(workflows)
    pending = gateway.dispatch("publish_stub", "task-1", {"draft_id": "draft-1"})
    assert pending.status == "awaiting_approval"
    result = gateway.dispatch("publish_stub", "task-1", {"draft_id": "draft-1"}, "approval-1")
    assert result.status == "stubbed"
    assert gateway.audit_log[0]["payload_keys"] == ["draft_id"]
    with pytest.raises(N8nGatewayError):
        gateway.dispatch("publish_stub", "task-1", {"token": "secret"}, "approval-1")

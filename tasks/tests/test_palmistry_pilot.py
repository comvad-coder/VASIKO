import json
from pathlib import Path


ROOT = Path(__file__).parents[1] / "palmistry-pilot"


def test_task_dossier_keeps_entities_separate():
    task = json.loads((ROOT / "task.json").read_text(encoding="utf-8"))
    assert task["task_id"] == "palmistry-pilot"
    assert task["status"] == "blocked"
    assert task["project"]["entity_id"] == "palm-promotion"
    assert task["products"] == [{"entity_type": "product", "entity_id": "palm"}]
    assert task["workspaces"] == [{"entity_type": "workspace", "entity_id": "palm-site"}]
    assert task["modules"] == [{"entity_type": "module", "entity_id": "promotion_engine"}]


def test_task_has_no_external_permissions_or_secret_material():
    task = json.loads((ROOT / "task.json").read_text(encoding="utf-8"))
    limits = task["limits"]
    assert limits["external_api_calls"] == 0
    assert limits["external_publications"] == 0
    assert limits["paid_actions"] == 0
    assert limits["credentials_access"] is False
    assert "token" not in json.dumps(task).lower()


def test_workspace_is_metadata_only_until_import():
    workspace = json.loads((ROOT.parent.parent / "workspaces/projects/palm-site/workspace.json").read_text(encoding="utf-8"))
    assert workspace["status"] == "not_imported"
    assert workspace["source"] is None
    assert workspace["changes_enabled"] is False
    assert workspace["release_enabled"] is False

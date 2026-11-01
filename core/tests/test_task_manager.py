import pytest

from core.domain import EntityRef, EntityType, TaskSpec, TaskStatus
from core.task_manager import LocalTaskManager


def test_task_is_persisted_and_resumed_from_checkpoint(tmp_path):
    manager = LocalTaskManager(tmp_path / "records")
    task = manager.create(TaskSpec(
        "pilot-1", "Analyze product", project=EntityRef(EntityType.PROJECT, "p1"),
        agents=[EntityRef(EntityType.AGENT, "planner")], tools=["url_analyzer"],
        limits={"budget": 0, "max_steps": 10}, qa_result="pending",
    ))
    manager.transition(task.task_id, TaskStatus.PLANNED)
    manager.transition(task.task_id, TaskStatus.RUNNING)
    manager.checkpoint(task.task_id, "product-analysis")

    reopened = LocalTaskManager(tmp_path / "records")
    assert reopened.get("pilot-1").checkpoints == ["product-analysis"]
    assert reopened.get("pilot-1").agents[0].entity_id == "planner"
    assert reopened.get("pilot-1").tools == ["url_analyzer"]
    assert reopened.get("pilot-1").limits["max_steps"] == 10
    assert reopened.get("pilot-1").qa_result == "pending"
    resumed = reopened.resume("pilot-1")
    assert resumed.status is TaskStatus.RUNNING
    assert resumed.next_step.endswith("product-analysis")


def test_invalid_transition_is_rejected(tmp_path):
    manager = LocalTaskManager(tmp_path / "records")
    manager.create(TaskSpec("pilot-2", "Test"))
    with pytest.raises(ValueError, match="запрещён"):
        manager.transition("pilot-2", TaskStatus.COMPLETED)


def test_task_id_path_traversal_is_rejected(tmp_path):
    manager = LocalTaskManager(tmp_path / "records")
    with pytest.raises(ValueError):
        manager.create(TaskSpec("../unsafe", "Test"))

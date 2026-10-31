from core.domain import EntityRef, EntityType, TaskSpec, TaskStatus


def test_task_keeps_product_and_workspace_as_explicit_refs():
    task = TaskSpec(
        task_id="task-1",
        objective="Pilot",
        project=EntityRef(EntityType.PROJECT, "project-1"),
        products=[EntityRef(EntityType.PRODUCT, "palm")],
        workspaces=[EntityRef(EntityType.WORKSPACE, "palm-site")],
    )
    assert task.status is TaskStatus.NEW
    assert task.products[0].entity_type is EntityType.PRODUCT
    assert task.workspaces[0].entity_type is EntityType.WORKSPACE
    assert task.project.entity_type is EntityType.PROJECT


def test_task_statuses_match_architecture_lifecycle():
    assert [status.value for status in TaskStatus][:4] == [
        "new", "planned", "awaiting_approval", "running"
    ]
    assert TaskStatus.ROLLED_BACK.value == "rolled_back"

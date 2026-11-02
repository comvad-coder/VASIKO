# Task index

Каждая задача содержит:

- `task_id` и `objective`;
- `project`, `products`, `workspaces` как отдельные ссылки;
- `agents` и `tools`;
- `limits`;
- `plan`;
- `status` по жизненному циклу Core;
- `checkpoints`;
- `artifacts`;
- `errors`;
- `qa_result`;
- `next_step`;
- даты создания и обновления.

Переходы статусов проверяются `core.task_manager.TRANSITIONS`. Возобновление прерванной задачи использует последний сохранённый checkpoint.

## Current task

`palmistry-pilot` находится в `tasks/palmistry-pilot/`. Это отдельная задача продвижения продукта Palm, связанная с project `palm-promotion`, product `palm`, workspace `palm-site` и модулем `promotion_engine`. Текущий статус — `blocked`: URL или ZIP Palm ещё не передан, поэтому внешние действия не разрешены.

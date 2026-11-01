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

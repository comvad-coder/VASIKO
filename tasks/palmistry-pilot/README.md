# palmistry-pilot

`palmistry-pilot` — обычная Task ВАСИКО по подготовке продвижения продукта Palm. Это не ядро ВАСИКО, не Gradio Admin и не отдельный главный проект.

## Entity separation

```text
Task      tasks/palmistry-pilot/
Project   projects/project-models/palm-promotion-project.md
Product   products/external-or-created-products/palm/
Workspace workspaces/projects/palm-site/
Module    modules/promotion_engine/
```

## Current status

`blocked`: пользователь ещё не передал подтверждённый URL Palm или ZIP сайта. Поэтому task содержит только metadata, draft plan и безопасные заглушки.

## Safety boundary

В Block 9 не выполняются HTTP-анализ сайта, реальные API-вызовы, публикации, рассылки, рекламные расходы, изменения workspace или работа с credentials. Любое внешнее действие требует отдельного approval.

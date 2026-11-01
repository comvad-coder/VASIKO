# Workspaces

Workspace — изолированная рабочая копия продукта, загруженная для конкретной задачи ВАСИКО.

```text
workspaces/projects/<workspace-id>/
├── workspace.json
├── original/          # сохранённый исходный ZIP
├── extracted/         # изолированная распакованная копия
├── analysis/          # import report и анализ стека
├── proposed-changes/  # будущие изменения до применения
├── tests/             # результаты тестов workspace
├── preview/           # будущий preview
├── backups/           # backup перед изменениями
└── releases/          # будущие release artifacts
```

ZIP проверяется до сохранения и распаковки. Блокируются path traversal, symlink, encrypted archives, подозрительный compression ratio, слишком большие архивы, секретные файлы и превышение лимитов. Изменения внешнего продукта и публикации в Block 7 не выполняются.

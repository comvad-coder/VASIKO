# project_workspace

Модуль безопасной загрузки ZIP и изолированной рабочей копии внешнего продукта. Gradio Admin вызывает его при запуске задачи с загруженным ZIP.

Импорт создаёт `original/`, `extracted/`, `analysis/import-report.json`, `proposed-changes/`, `tests/`, `preview/`, `backups/` и `releases/`. Оригинал не изменяется.

Существующий metadata-only workspace может быть заменён первым импортом только через явный `allow_metadata_stub=True`; прежний descriptor сохраняется в `backups/pre-import-workspace.json`. Path traversal, symlink, encrypted ZIP, secret-like files и превышение лимитов блокируются.

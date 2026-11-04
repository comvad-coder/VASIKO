# project_workspace

Модуль безопасной загрузки ZIP и изолированной рабочей копии внешнего продукта. Gradio Admin вызывает его при запуске задачи с загруженным ZIP.

Импорт создаёт `original/`, `extracted/`, `analysis/import-report.json`, `proposed-changes/`, `tests/`, `preview/`, `backups/` и `releases/`. Оригинал не изменяется.

Существующий непустой workspace при запуске из Admin сначала переносится в `workspaces/projects/_archive/<workspace-id>/<timestamp>/`, затем новый импорт создаётся в исходном пути. Metadata-only workspace также сохраняется как backup. При ошибке распаковки старый workspace возвращается обратно. Path traversal, symlink, encrypted ZIP, secret-like files и превышение лимитов блокируются.

# VASIKO Gradio Admin — Block 1

Первый блок реализует отдельную административную панель ВАСИКО. Это не Palm и не `palmistry-pilot`.

## Границы

- локальный Admin adapter с persistent JSON state вместо полноценного Core;
- локальные JSON snapshots вместо полноценного Backup Service;
- диагностика показывает состояние заглушек;
- URL принимается как вход; ZIP после создания задачи импортируется кнопкой «Запустить» через `project_workspace`;
- URL-задача после создания и подтверждения запускает read-only `website_url_check` skill, а не stub;
- URL-отчёты сохраняются в `workspaces/projects/<workspace-id>/analysis/url-check-report.json` и `.md`;
- оригинал сохраняется в `workspaces/projects/<workspace-id>/original/`, копия распаковывается в `extracted/`, отчёт создаётся в `analysis/import-report.json`;
- небезопасные ZIP блокируются, а задача получает статус `blocked`;
- публикации, рассылки, платежи, аккаунты и реальные credentials отсутствуют.

## Запуск

```bash
python3 -m pip install -r F:\Projects\vasiko\admin\gradio_admin\requirements.txt
python F:\Projects\vasiko\admin\gradio_admin\app.py
```

Точка запуска: `F:\Projects\vasiko\admin\gradio_admin\app.py`. Альтернативный запуск из корня: `python -m admin.gradio_admin.app`.

## Разделы

Dashboard, Tasks, Products, Workspaces, Agents, Skills, Modules, Integrations, n8n, Promotion, Content, Video, Publications, Analytics, Approvals, Memory, Backups, Diagnostics, Recovery, Settings и Action Log.

Функционально работают создание задачи, просмотр статусов, URL/ZIP входы, просмотр плана, approval, URL-check, built-in AI product analysis через skill, ZIP import, остановка, журнал, backup и diagnostics. Остальные разделы являются явными заглушками.

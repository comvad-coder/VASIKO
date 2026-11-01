# VASIKO Gradio Admin — Block 1

Первый блок реализует отдельную административную панель ВАСИКО. Это не Palm и не `palmistry-pilot`.

## Границы

- локальный in-memory stub вместо Core;
- локальные JSON snapshots вместо полноценного Backup Service;
- диагностика показывает состояние заглушек;
- URL и ZIP принимаются как входы, но внешние API не вызываются, ZIP не распаковывается;
- публикации, рассылки, платежи, аккаунты и реальные credentials отсутствуют.

## Запуск

```bash
python3 -m pip install -r requirements.txt
python3 admin/gradio_admin/app.py
```

Точка запуска: `admin/gradio_admin/app.py`.

## Разделы

Dashboard, Tasks, Products, Workspaces, Agents, Skills, Modules, Integrations, n8n, Promotion, Content, Video, Publications, Analytics, Approvals, Memory, Backups, Diagnostics, Recovery, Settings и Action Log.

Функционально в первом блоке работают создание задачи, просмотр статусов, URL/ZIP входы, просмотр плана, approval, запуск/остановка, журнал, backup и diagnostics. Остальные разделы являются явными заглушками.

# VASIKO Core — Blocks 2–4

Core — стабильный слой доменных типов, задач, локальной памяти, самосохранения и правил ВАСИКО. Реальные внешние интеграции, n8n, orchestrator и credentials пока не подключены.

## Структура

- `domain.py` — отдельные типы Task/Product/Project/Workspace/Module/Skill/Agent/Integration/n8n Workflow и жизненный цикл задачи.
- `policy.py` — правило: внутренние безопасные действия допустимы, внешние и рискованные требуют approval.
- `ports.py` — интерфейсы будущих адаптеров Task Repository, Audit Log, Approval Gateway и Health Probe.
- `system_state.py` — локальная модель диагностики состояния ядра.
- `task_manager.py` — локальный JSON Task Manager с lifecycle, checkpoint и resume.
- `memory_store.py` — разделённая JSONL-память с search/export/delete и secret guard.
- `backup_manager.py` — snapshot, manifest и SHA-256 для самого ВАСИКО.
- `diagnostics.py` — System Health проверки Core, Admin, данных, диска и backup.
- `recovery.py` — guarded recovery с pre-restore snapshot и approval.

Admin пока не импортирует Core: интеграция Admin → Core будет отдельным проверяемым изменением после стабилизации этого блока.

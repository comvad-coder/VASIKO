# VASIKO Core — Block 2

Core — стабильный слой доменных типов и правил ВАСИКО. В этом блоке нет базы данных, реальных интеграций, n8n, памяти, orchestrator и внешних API.

## Структура

- `domain.py` — отдельные типы Task/Product/Project/Workspace/Module/Skill/Agent/Integration/n8n Workflow и жизненный цикл задачи.
- `policy.py` — правило: внутренние безопасные действия допустимы, внешние и рискованные требуют approval.
- `ports.py` — интерфейсы будущих адаптеров Task Repository, Audit Log, Approval Gateway и Health Probe.
- `system_state.py` — локальная модель диагностики состояния ядра.

Admin пока не импортирует Core: интеграция Admin → Core будет отдельным проверяемым изменением после стабилизации этого блока.

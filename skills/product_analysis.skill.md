# Product Analysis Skill

## Назначение

Анализирует только уже созданный `url-check-report.json` и цель задачи. Использует built-in AI через `manus-node` и структурированный JSON schema output.

## Модель

Текущий model ID: `gpt-6-luna`. Он выбран из live catalog как доступный недорогой structured-analysis model с поддержкой JSON schema.

## Вход

- `analysis/url-check-report.json`;
- цель задачи;
- `task_id`;
- workspace.

## Выход

- `analysis/product-analysis-report.json`;
- `analysis/product-analysis-report.md`.

Результат содержит summary, positioning, audience, value propositions, strengths, risks/gaps, recommended channels, next internal actions и confidence.

## Безопасность

Skill не публикует, не отправляет сообщения, не тратит деньги, не использует credentials и не изменяет сайт. AI получает только URL-check report и цель задачи. Его результат является советом для внутреннего review и не запускает promotion execution.

## Runtime

Исполняемый runner: `skills/product_analysis_runner.mjs`. Он использует `manus-node` и bundled built-in LLM runtime. При недоступном runtime задача блокируется с явной ошибкой, без перехода к stub или внешнему действию.

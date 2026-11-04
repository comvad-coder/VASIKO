# VASIKO n8n

n8n — технический automation layer. Бизнес-решение о запуске остаётся в Core и approval policy.

## Workflow product-analysis

Файл импорта:

```text
F:\Projects\vasiko\n8n\import-export\vasiko-product-analysis.workflow.json
```

Workflow делает:

```text
Webhook POST /webhook/vasiko/product-analysis
→ подготовка prompt из URL-check report
→ AI Product Analysis
→ нормализация JSON
→ ответ webhook
```

В workflow нет credentials. После импорта в n8n нужно выбрать credential для узла `AI Product Analysis` с именем `VASIKO_AI`. Credential хранится только в n8n, не в GitHub.

## Подключение Admin

После активации workflow в n8n на ПК задать в PowerShell:

```powershell
$env:VASIKO_N8N_PRODUCT_ANALYSIS_URL = 'http://localhost:5678/webhook/vasiko/product-analysis'
```

Затем запустить Admin из того же окна PowerShell:

```powershell
python 'F:\Projects\vasiko\admin\gradio_admin\app.py'
```

Если переменная не задана, skill использует Manus built-in runtime. Если переменная задана, запрос идёт только в локальный n8n webhook.

## Безопасность

Workflow принимает только URL-check report и цель задачи. Публикации, рассылки, платежи, изменения сайта и другие внешние действия не выполняются. Workflow импортируется выключенным; его нужно активировать вручную после выбора AI credential.

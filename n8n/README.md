# VASIKO n8n

n8n — технический automation layer. Бизнес-решение о запуске остаётся в Core и approval policy.

```text
n8n/
├── workflows/       # manifests/export будущих workflows
├── templates/       # безопасные шаблоны
├── fixtures/        # тестовые payloads без secrets
└── import-export/   # контролируемые import/export артефакты
```

В Block 6 реальные n8n workflows и credentials не подключены. Все dispatch-операции проходят через `integrations/n8n_gateway/gateway.py`.

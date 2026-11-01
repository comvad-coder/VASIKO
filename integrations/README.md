# VASIKO integrations

`integrations/` — единый слой внешних подключений. Внешний сервис не вызывается напрямую из задач или модулей.

`registry/` хранит connector manifests; `credentials_policy/` разрешает только ссылки на credentials; `n8n_gateway/` является границей технических workflows.

Каталоги `ai`, `research`, `analytics`, `social_platforms`, `crm`, `payments`, `storage` и `notifications` пока являются placeholders. Реальные API, платежи, публикации, OAuth и credentials в Block 6 не подключаются.

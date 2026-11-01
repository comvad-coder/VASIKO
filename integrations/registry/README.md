# Connector registry

Connector manifest описывает `integration_id`, provider, category, scopes, capabilities и ссылку `credential_ref`. Секреты и реальные значения credentials запрещены.

Статусы: `stubbed`, `disabled`, `not_connected`, `connected`. Переход в `connected` требует `approval_id`; в Block 6 registry остаётся без реальных подключений.

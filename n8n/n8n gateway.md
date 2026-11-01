# n8n gateway

Gateway принимает только зарегистрированные workflow и не принимает архитектурные решения вместо Core. Внешний workflow без `approval_id` получает статус `awaiting_approval`. После approval Block 6 возвращает `stubbed`: реальный HTTP/n8n вызов ещё не выполняется.

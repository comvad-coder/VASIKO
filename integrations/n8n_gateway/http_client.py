"""HTTP client for approved local n8n webhooks."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class N8nHTTPError(RuntimeError):
    pass


class N8nWebhookClient:
    def __init__(self, webhook_url: str | None = None, timeout_seconds: int = 120) -> None:
        self.webhook_url = (webhook_url or os.getenv("VASIKO_N8N_PRODUCT_ANALYSIS_URL", "")).strip()
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.webhook_url)

    def product_analysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.webhook_url:
            raise N8nHTTPError("VASIKO_N8N_PRODUCT_ANALYSIS_URL не настроен")
        if not self.webhook_url.startswith("http://localhost:") and not self.webhook_url.startswith("http://127.0.0.1:"):
            raise N8nHTTPError("n8n webhook должен быть локальным localhost/127.0.0.1")
        request = urllib.request.Request(
            self.webhook_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "VASIKO-n8n-gateway/0.1"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(4 * 1024 * 1024)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise N8nHTTPError(f"n8n webhook недоступен: {exc}") from exc
        try:
            result = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise N8nHTTPError("n8n вернул невалидный JSON") from exc
        if not isinstance(result, dict) or "analysis" not in result:
            raise N8nHTTPError("n8n response не содержит analysis")
        return result

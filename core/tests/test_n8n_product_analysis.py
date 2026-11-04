import json
from pathlib import Path

import pytest

from integrations.n8n_gateway.http_client import N8nHTTPError, N8nWebhookClient
from skills.product_analysis import ProductAnalysisSkill


def test_n8n_client_requires_local_webhook():
    client = N8nWebhookClient("https://example.test/webhook")
    with pytest.raises(N8nHTTPError, match="локальным"):
        client.product_analysis({"objective": "test"})


def test_product_analysis_uses_n8n_response(tmp_path, monkeypatch):
    report_path = tmp_path / "analysis" / "url-check-report.json"
    report_path.parent.mkdir()
    report_path.write_text(json.dumps({"requested_url": "https://example.test", "status_code": 200}), encoding="utf-8")

    class FakeClient:
        enabled = True

        def product_analysis(self, payload):
            assert payload["objective"] == "Поиск клиентов"
            return {
                "provider": "n8n-local",
                "model": "configured-n8n-ai",
                "analysis": {
                    "executive_summary": "ok",
                    "product_positioning": "",
                    "target_audience": [],
                    "value_propositions": [],
                    "strengths": [],
                    "risks_and_gaps": [],
                    "recommended_channels": [],
                    "next_internal_actions": [],
                    "confidence": "medium",
                },
            }

    monkeypatch.setattr("skills.product_analysis.N8nWebhookClient", lambda: FakeClient())
    result = ProductAnalysisSkill().analyze(report_path, tmp_path, "task-1", "Поиск клиентов")

    assert result.provider == "n8n-local"
    assert result.model == "configured-n8n-ai"
    assert (tmp_path / "analysis" / "product-analysis-report.json").is_file()

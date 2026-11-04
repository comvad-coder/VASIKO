from email.message import Message

import pytest

from skills.website_url_check import URLInspectionError, WebsiteURLCheckSkill


class FakeResponse:
    status = 200

    def __init__(self, body: bytes):
        self._body = body
        self.headers = Message()
        self.headers["Content-Type"] = "text/html; charset=utf-8"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self._body if size < 0 else self._body[:size]

    def geturl(self):
        return "https://example.test/"


def test_url_check_extracts_signals_and_writes_reports(tmp_path, monkeypatch):
    body = b"""
    <html><head><title>Palm Test</title>
    <meta name='description' content='Find clients'></head>
    <body><h1>Consulting</h1><a href='/contact'>Contact</a>
    <script src='/_next/static/app.js'></script></body></html>
    """
    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: FakeResponse(body))

    report = WebsiteURLCheckSkill().inspect("https://example.test/", tmp_path, "task-1")

    assert report.status_code == 200
    assert report.title == "Palm Test"
    assert report.meta_description == "Find clients"
    assert report.h1 == ["Consulting"]
    assert report.link_count == 1
    assert "next" in report.technical_signals
    assert (tmp_path / "analysis" / "url-check-report.json").is_file()
    assert (tmp_path / "analysis" / "url-check-report.md").is_file()


def test_url_check_rejects_local_and_credential_urls(tmp_path):
    skill = WebsiteURLCheckSkill()
    with pytest.raises(URLInspectionError, match="Локальные"):
        skill.inspect("http://127.0.0.1:8000", tmp_path)
    with pytest.raises(URLInspectionError, match="логином"):
        skill.inspect("https://user:pass@example.test", tmp_path)

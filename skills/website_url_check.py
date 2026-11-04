"""Local website URL inspection skill.

This skill performs a read-only HTTP inspection. It does not use AI, credentials,
external APIs, publishing, payments, or website mutations.
"""
from __future__ import annotations

import json
import re
import socket
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlparse


class URLInspectionError(ValueError):
    """Raised when URL inspection cannot safely be performed."""


@dataclass
class URLInspectionReport:
    checked_at: str
    requested_url: str
    final_url: str = ""
    status_code: int = 0
    content_type: str = ""
    response_bytes: int = 0
    title: str = ""
    meta_description: str = ""
    h1: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    link_count: int = 0
    technical_signals: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    external_actions: bool = False


class _HTMLSignals(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta_description = ""
        self.h1: list[str] = []
        self.links: list[str] = []
        self._in_title = False
        self._in_h1 = False
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "title":
            self._in_title = True
            self._text = []
        elif tag == "h1":
            self._in_h1 = True
            self._text = []
        elif tag == "meta" and attributes.get("name", "").lower() == "description":
            self.meta_description = (attributes.get("content") or "").strip()
        elif tag == "a" and attributes.get("href"):
            href = attributes["href"].strip()
            if href and href not in self.links and len(self.links) < 100:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._in_title:
            self.title = " ".join("".join(self._text).split())[:500]
            self._in_title = False
        elif tag == "h1" and self._in_h1:
            value = " ".join("".join(self._text).split())
            if value and value not in self.h1 and len(self.h1) < 20:
                self.h1.append(value[:500])
            self._in_h1 = False

    def handle_data(self, data: str) -> None:
        if self._in_title or self._in_h1:
            self._text.append(data)


class WebsiteURLCheckSkill:
    def __init__(self, timeout_seconds: float = 15.0, max_response_bytes: int = 2 * 1024 * 1024) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes

    def inspect(self, url: str, workspace_root: str | Path, task_id: str = "") -> URLInspectionReport:
        normalized = self._validate_url(url)
        request = urllib.request.Request(
            normalized,
            headers={
                "User-Agent": "VASIKO-URL-Check/0.1 (read-only inspection)",
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read(self.max_response_bytes + 1)
                if len(body) > self.max_response_bytes:
                    body = body[: self.max_response_bytes]
                    truncated = True
                else:
                    truncated = False
                content_type = response.headers.get_content_type()
                final_url = response.geturl()
                status = int(response.status)
        except urllib.error.HTTPError as exc:
            body = exc.read(self.max_response_bytes)
            content_type = exc.headers.get_content_type() if exc.headers else ""
            final_url = exc.geturl()
            status = int(exc.code)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise URLInspectionError(f"URL недоступен: {exc}") from exc

        parser = _HTMLSignals()
        notes: list[str] = []
        if content_type in {"text/html", "application/xhtml+xml"}:
            charset = "utf-8"
            try:
                declared = response.headers.get_content_charset()  # type: ignore[name-defined]
                charset = declared or charset
            except NameError:
                pass
            parser.feed(body.decode(charset, errors="replace"))
        else:
            notes.append(f"content-type={content_type or 'unknown'}; HTML signals were not parsed")

        signals = self._technical_signals(body, content_type)
        if truncated:
            notes.append(f"response truncated at {self.max_response_bytes} bytes")
        if status >= 400:
            notes.append("HTTP response indicates an error status")
        if not parser.title:
            notes.append("title not found")
        if not parser.meta_description:
            notes.append("meta description not found")
        if not parser.h1:
            notes.append("h1 not found")

        report = URLInspectionReport(
            checked_at=datetime.now(timezone.utc).isoformat(),
            requested_url=normalized,
            final_url=final_url,
            status_code=status,
            content_type=content_type,
            response_bytes=len(body),
            title=parser.title,
            meta_description=parser.meta_description,
            h1=parser.h1,
            links=parser.links,
            link_count=len(parser.links),
            technical_signals=signals,
            notes=notes,
        )
        self._write_reports(Path(workspace_root), report, task_id)
        return report

    @staticmethod
    def _validate_url(url: str) -> str:
        value = (url or "").strip()
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise URLInspectionError("Нужен полный публичный URL с http:// или https://")
        if parsed.username or parsed.password:
            raise URLInspectionError("URL с логином или паролем запрещён")
        hostname = parsed.hostname.lower().rstrip(".")
        if hostname in {"localhost", "localhost.localdomain"}:
            raise URLInspectionError("Локальные адреса запрещены для URL-check")
        try:
            address = ip_address(hostname)
        except ValueError:
            address = None
        if address is not None and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
            raise URLInspectionError("Локальные и приватные IP-адреса запрещены")
        return value

    @staticmethod
    def _technical_signals(body: bytes, content_type: str) -> list[str]:
        text = body.decode("utf-8", errors="ignore")
        signals: list[str] = []
        patterns = {
            "react": r"(?:react|react-dom)",
            "next": r"(?:__next|next/static)",
            "vite": r"(?:vite|@vite/client)",
            "vue": r"(?:vue(?:\.runtime)?\.js|__vue__)",
            "tailwind": r"tailwind",
            "netlify": r"netlify",
        }
        for name, pattern in patterns.items():
            if re.search(pattern, text, re.I):
                signals.append(name)
        if content_type in {"text/html", "application/xhtml+xml"}:
            signals.append("html")
        return signals

    @staticmethod
    def _write_reports(workspace_root: Path, report: URLInspectionReport, task_id: str) -> None:
        analysis = workspace_root / "analysis"
        analysis.mkdir(parents=True, exist_ok=True)
        payload = asdict(report)
        if task_id:
            payload["task_id"] = task_id
        note_lines = [f"- {note}" for note in report.notes] or ["- No notes"]
        (analysis / "url-check-report.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        lines = [
            "# URL check report",
            "",
            f"- Requested URL: `{report.requested_url}`",
            f"- Final URL: `{report.final_url}`",
            f"- HTTP status: `{report.status_code}`",
            f"- Content type: `{report.content_type}`",
            f"- Response bytes: `{report.response_bytes}`",
            f"- Title: {report.title or '(not found)'}",
            f"- Meta description: {report.meta_description or '(not found)'}",
            f"- H1: {', '.join(report.h1) or '(not found)'}",
            f"- Link count: `{report.link_count}`",
            f"- Technical signals: {', '.join(report.technical_signals) or '(none detected)'}",
            "",
            "## Notes",
            *note_lines,
            "",
            "Read-only inspection. No AI, credentials, publishing, payments, or website changes were used.",
        ]
        (analysis / "url-check-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_url(url: str, workspace_root: str | Path, task_id: str = "") -> URLInspectionReport:
    return WebsiteURLCheckSkill().inspect(url, workspace_root, task_id)

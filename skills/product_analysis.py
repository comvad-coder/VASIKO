"""AI-backed product analysis skill for URL-check reports."""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


class ProductAnalysisError(ValueError):
    """Raised when the built-in AI analysis cannot be completed."""


@dataclass
class ProductAnalysisResult:
    task_id: str
    product_url: str
    provider: str
    model: str
    analyzed_at: str
    analysis: dict
    usage: dict | None = None


class ProductAnalysisSkill:
    def __init__(self, runner: str | Path | None = None, timeout_seconds: int = 150) -> None:
        self.runner = Path(runner) if runner else Path(__file__).with_name("product_analysis_runner.mjs")
        self.timeout_seconds = timeout_seconds

    def analyze(
        self,
        url_report_path: str | Path,
        workspace_root: str | Path,
        task_id: str,
        objective: str,
    ) -> ProductAnalysisResult:
        report_path = Path(url_report_path)
        if not report_path.is_file():
            raise ProductAnalysisError(f"URL-check report not found: {report_path}")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        payload = {
            "objective": objective,
            "product_url": report.get("requested_url", ""),
            "url_check_report": report,
        }
        env = os.environ.copy()
        try:
            completed = subprocess.run(
                ["manus-node", str(self.runner)],
                input=json.dumps(payload, ensure_ascii=False),
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                env=env,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProductAnalysisError(f"Built-in AI runner unavailable: {exc}") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "unknown AI runner error").strip()
            raise ProductAnalysisError(f"Built-in AI analysis failed: {detail[-2000:]}")
        try:
            result = json.loads(completed.stdout)
            analysis = result["analysis"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ProductAnalysisError("Built-in AI returned invalid structured output") from exc

        output = ProductAnalysisResult(
            task_id=task_id,
            product_url=report.get("requested_url", ""),
            provider=result.get("provider", "manus-builtin"),
            model=result.get("model", "gpt-6-luna"),
            analyzed_at=datetime.now(timezone.utc).isoformat(),
            analysis=analysis,
            usage=result.get("usage"),
        )
        self._write_reports(Path(workspace_root), output)
        return output

    @staticmethod
    def _write_reports(workspace_root: Path, result: ProductAnalysisResult) -> None:
        analysis_dir = workspace_root / "analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        payload = asdict(result)
        (analysis_dir / "product-analysis-report.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        data = result.analysis
        lines = [
            "# Product analysis report",
            "",
            f"- Task: `{result.task_id}`",
            f"- URL: `{result.product_url}`",
            f"- Provider: `{result.provider}`",
            f"- Model: `{result.model}`",
            f"- Confidence: `{data.get('confidence', 'unknown')}`",
            "",
            "## Executive summary",
            data.get("executive_summary", ""),
            "",
            "## Product positioning",
            data.get("product_positioning", ""),
        ]
        for title, key in (
            ("Target audience", "target_audience"),
            ("Value propositions", "value_propositions"),
            ("Strengths", "strengths"),
            ("Risks and gaps", "risks_and_gaps"),
            ("Recommended channels", "recommended_channels"),
            ("Next internal actions", "next_internal_actions"),
        ):
            lines.extend(["", f"## {title}"])
            lines.extend(f"- {item}" for item in data.get(key, []))
        lines.extend([
            "",
            "AI analysis is advisory and local. No publication, payment, message, credential access, or website mutation was performed.",
        ])
        (analysis_dir / "product-analysis-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

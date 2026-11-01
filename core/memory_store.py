"""Partitioned local JSONL memory store for VASIKO Block 3."""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class MemoryKind(str, Enum):
    EVENTS = "events"
    TASKS = "tasks"
    PROJECTS = "projects"
    KNOWLEDGE = "knowledge"
    PROCEDURES = "procedures"
    PREFERENCES = "preferences"


class MemorySafetyError(ValueError):
    """Raised when data resembles a secret or credential."""


SENSITIVE_KEY = re.compile(r"(?:api[_-]?key|password|passwd|token|secret|private[_-]?key|credential|credit[_-]?card)", re.I)
SENSITIVE_VALUE = re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9]{20,}|bearer\s+[A-Za-z0-9._-]{12,})", re.I)


@dataclass(frozen=True)
class MemoryRecord:
    record_id: str
    kind: MemoryKind
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _check_safe(value: Any, path: str = "value") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if SENSITIVE_KEY.search(str(key)):
                raise MemorySafetyError(f"Секретное поле запрещено в памяти: {path}.{key}")
            _check_safe(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _check_safe(item, f"{path}[{index}]")
    elif isinstance(value, str) and SENSITIVE_VALUE.search(value):
        raise MemorySafetyError(f"Похоже на credential в поле {path}")


class LocalMemoryStore:
    def __init__(self, root: str | Path = "memory") -> None:
        self.root = Path(root)
        for kind in MemoryKind:
            (self.root / kind.value).mkdir(parents=True, exist_ok=True)

    def _path(self, kind: MemoryKind) -> Path:
        return self.root / kind.value / "records.jsonl"

    def append(self, kind: MemoryKind, content: str, metadata: dict[str, Any] | None = None) -> MemoryRecord:
        if not content or not content.strip():
            raise ValueError("Содержимое записи памяти не может быть пустым")
        metadata = metadata or {}
        _check_safe(content, "content")
        _check_safe(metadata, "metadata")
        record = MemoryRecord(f"mem-{uuid.uuid4().hex[:12]}", kind, content.strip(), metadata)
        with self._path(kind).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record) | {"kind": kind.value}, ensure_ascii=False) + "\n")
        return record

    def _read(self, kind: MemoryKind) -> list[MemoryRecord]:
        path = self._path(kind)
        if not path.exists():
            return []
        records: list[MemoryRecord] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                data = json.loads(line)
                records.append(MemoryRecord(data["record_id"], MemoryKind(data["kind"]), data["content"], data.get("metadata", {}), data["created_at"]))
        return records

    def search(self, query: str, kind: MemoryKind | None = None) -> list[MemoryRecord]:
        query = (query or "").strip().casefold()
        if not query:
            return []
        kinds = [kind] if kind else list(MemoryKind)
        result: list[MemoryRecord] = []
        for current in kinds:
            for record in self._read(current):
                haystack = f"{record.content} {json.dumps(record.metadata, ensure_ascii=False)}".casefold()
                if query in haystack:
                    result.append(record)
        return result

    def export(self, kind: MemoryKind | None = None) -> list[dict[str, Any]]:
        kinds = [kind] if kind else list(MemoryKind)
        return [asdict(record) | {"kind": record.kind.value} for current in kinds for record in self._read(current)]

    def export_to(self, destination: str | Path, kind: MemoryKind | None = None) -> Path:
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.export(kind), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target

    def delete(self, record_id: str) -> bool:
        for kind in MemoryKind:
            records = self._read(kind)
            remaining = [record for record in records if record.record_id != record_id]
            if len(remaining) != len(records):
                path = self._path(kind)
                path.write_text("".join(json.dumps(asdict(record) | {"kind": record.kind.value}, ensure_ascii=False) + "\n" for record in remaining), encoding="utf-8")
                return True
        return False

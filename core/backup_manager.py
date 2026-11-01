"""Local, integrity-checked backup service for VASIKO itself."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tarfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


class BackupError(RuntimeError):
    pass


SECRET_NAME = re.compile(r"(?:\.env|credential|password|secret|token|private[_-]?key)", re.I)
EXCLUDED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "backups"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tar", ".tar.gz", ".zip"}


@dataclass(frozen=True)
class BackupManifest:
    backup_id: str
    label: str
    created_at: str
    source_root: str
    archive: str
    archive_sha256: str
    version: str
    file_count: int
    excluded_policy: str = "No .env/credentials/secrets; no VCS, virtualenv, caches or nested backups"


class BackupManager:
    def __init__(self, source_root: str | Path, backup_root: str | Path = "backups/vasiko", version: str = "block-4") -> None:
        self.source_root = Path(source_root).resolve()
        self.backup_root = Path(backup_root)
        self.version = version
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def _excluded(self, relative: Path) -> bool:
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            return True
        if any(SECRET_NAME.search(part) for part in relative.parts):
            return True
        name = relative.name.lower()
        return any(name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES) or name.startswith("pre-block")

    def _files(self) -> list[Path]:
        if not self.source_root.exists():
            raise BackupError(f"Source root not found: {self.source_root}")
        return sorted(path for path in self.source_root.rglob("*") if path.is_file() and not self._excluded(path.relative_to(self.source_root)))

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def create_snapshot(self, label: str = "vasiko") -> Path:
        safe_label = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-") or "vasiko"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = self.backup_root / f"{safe_label}-{stamp}.tar.gz"
        files = self._files()
        with tarfile.open(archive, "w:gz") as bundle:
            for path in files:
                bundle.add(path, arcname=path.relative_to(self.source_root).as_posix(), recursive=False)
        manifest = BackupManifest(
            backup_id=f"backup-{uuid.uuid4().hex[:12]}", label=safe_label,
            created_at=datetime.now(timezone.utc).isoformat(), source_root=str(self.source_root),
            archive=archive.name, archive_sha256=self._sha256(archive), version=self.version,
            file_count=len(files),
        )
        archive.with_suffix(archive.suffix + ".manifest.json").write_text(
            json.dumps(asdict(manifest), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return archive

    def verify(self, archive: str | Path) -> BackupManifest:
        archive = Path(archive)
        manifest_path = archive.with_suffix(archive.suffix + ".manifest.json")
        if not archive.is_file() or not manifest_path.is_file():
            raise BackupError("Архив или manifest не найден")
        manifest = BackupManifest(**json.loads(manifest_path.read_text(encoding="utf-8")))
        if manifest.archive_sha256 != self._sha256(archive):
            raise BackupError("SHA-256 резервной копии не совпадает")
        try:
            with tarfile.open(archive, "r:gz") as bundle:
                bundle.getmembers()
        except (tarfile.TarError, OSError) as exc:
            raise BackupError(f"Архив повреждён: {exc}") from exc
        return manifest

    def latest(self) -> Path | None:
        archives = sorted(self.backup_root.glob("*.tar.gz"))
        return archives[-1] if archives else None

    def list_verified(self) -> list[Path]:
        verified: list[Path] = []
        for archive in sorted(self.backup_root.glob("*.tar.gz")):
            try:
                self.verify(archive)
                verified.append(archive)
            except BackupError:
                continue
        return verified

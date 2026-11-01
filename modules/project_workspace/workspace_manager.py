"""Safe ZIP import into isolated VASIKO project workspaces."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable


class WorkspaceError(ValueError):
    pass


WORKSPACE_ID = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
SECRET_NAME = re.compile(r"(?:^\.env$|credentials?|password|secret|token|private[_-]?key|id_rsa)", re.I)
STACK_FILES = {
    "package.json": "node",
    "pnpm-lock.yaml": "node",
    "yarn.lock": "node",
    "package-lock.json": "node",
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "Pipfile": "python",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "composer.json": "php",
    "Dockerfile": "container",
}


@dataclass(frozen=True)
class WorkspacePolicy:
    max_archive_bytes: int = 50 * 1024 * 1024
    max_uncompressed_bytes: int = 250 * 1024 * 1024
    max_files: int = 5000
    max_file_bytes: int = 25 * 1024 * 1024
    max_compression_ratio: int = 100


@dataclass
class WorkspaceManifest:
    workspace_id: str
    product_id: str
    status: str
    created_at: str
    source_archive_sha256: str
    file_count: int
    uncompressed_bytes: int
    detected_stacks: list[str] = field(default_factory=list)
    source_name: str = ""
    backup_count: int = 0


class WorkspaceManager:
    def __init__(self, root: str | Path = "workspaces/projects", policy: WorkspacePolicy | None = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.policy = policy or WorkspacePolicy()

    def workspace_path(self, workspace_id: str) -> Path:
        self._validate_id(workspace_id)
        return self.root / workspace_id

    def import_zip(self, archive: str | Path, workspace_id: str, product_id: str = "external_product") -> WorkspaceManifest:
        archive = Path(archive)
        self._validate_id(workspace_id)
        self._validate_id(product_id)
        self._validate_archive_file(archive)
        with zipfile.ZipFile(archive, "r") as bundle:
            entries = self._validate_entries(bundle)
            stack_files = [entry.filename.rsplit("/", 1)[-1] for entry in entries]
            stacks = sorted({STACK_FILES[name] for name in stack_files if name in STACK_FILES})

        target = self.workspace_path(workspace_id)
        if target.exists() and any(target.iterdir()):
            raise WorkspaceError(f"Workspace уже существует и не пуст: {workspace_id}")
        target.mkdir(parents=True, exist_ok=True)
        for directory in ("original", "extracted", "analysis", "proposed-changes", "tests", "preview", "backups", "releases"):
            (target / directory).mkdir(parents=True, exist_ok=True)

        original = target / "original" / archive.name
        shutil.copy2(archive, original)
        digest = self._sha256(original)
        extracted = target / "extracted"
        try:
            with zipfile.ZipFile(original, "r") as bundle:
                for entry in self._validate_entries(bundle):
                    relative = self._safe_relative(entry.filename)
                    destination = extracted / relative
                    if entry.is_dir():
                        destination.mkdir(parents=True, exist_ok=True)
                        continue
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(entry, "r") as source, destination.open("wb") as output:
                        shutil.copyfileobj(source, output, length=1024 * 1024)
                    os.chmod(destination, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        except (OSError, zipfile.BadZipFile) as exc:
            shutil.rmtree(target, ignore_errors=True)
            raise WorkspaceError(f"Распаковка workspace не выполнена: {exc}") from exc

        manifest = WorkspaceManifest(
            workspace_id=workspace_id, product_id=product_id, status="imported",
            created_at=datetime.now(timezone.utc).isoformat(), source_archive_sha256=digest,
            file_count=len(entries), uncompressed_bytes=sum(entry.file_size for entry in entries),
            detected_stacks=stacks, source_name=archive.name,
        )
        self._write_manifest(target, manifest)
        (target / "analysis" / "import-report.json").write_text(
            json.dumps({"workspace_id": workspace_id, "status": manifest.status, "file_count": manifest.file_count,
                        "uncompressed_bytes": manifest.uncompressed_bytes, "detected_stacks": stacks},
                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return manifest

    def create_change_backup(self, workspace_id: str) -> Path:
        target = self.workspace_path(workspace_id)
        extracted = target / "extracted"
        if not extracted.is_dir():
            raise WorkspaceError("Нельзя создать backup: extracted workspace не найден")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = target / "backups" / stamp
        shutil.copytree(extracted, backup)
        manifest = self._read_manifest(target)
        manifest.backup_count += 1
        self._write_manifest(target, manifest)
        return backup

    def _validate_archive_file(self, archive: Path) -> None:
        if not archive.is_file() or archive.suffix.lower() != ".zip":
            raise WorkspaceError("Нужен существующий ZIP-файл")
        if archive.stat().st_size > self.policy.max_archive_bytes:
            raise WorkspaceError("ZIP превышает допустимый размер")
        try:
            with zipfile.ZipFile(archive, "r") as bundle:
                if bundle.testzip() is not None:
                    raise WorkspaceError("ZIP содержит повреждённый файл")
        except zipfile.BadZipFile as exc:
            raise WorkspaceError("Файл не является корректным ZIP") from exc

    def _validate_entries(self, bundle: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
        entries = bundle.infolist()
        if len(entries) > self.policy.max_files:
            raise WorkspaceError("ZIP содержит слишком много файлов")
        total = 0
        for entry in entries:
            self._safe_relative(entry.filename)
            if SECRET_NAME.search(Path(entry.filename).name):
                raise WorkspaceError(f"ZIP содержит потенциальный секретный файл: {entry.filename}")
            mode = (entry.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise WorkspaceError(f"Symlink в ZIP запрещён: {entry.filename}")
            if entry.flag_bits & 0x1:
                raise WorkspaceError("Зашифрованные ZIP-файлы запрещены")
            if entry.file_size > self.policy.max_file_bytes:
                raise WorkspaceError(f"Файл превышает лимит: {entry.filename}")
            if entry.compress_size and entry.file_size / entry.compress_size > self.policy.max_compression_ratio:
                raise WorkspaceError(f"Подозрительный compression ratio: {entry.filename}")
            total += entry.file_size
        if total > self.policy.max_uncompressed_bytes:
            raise WorkspaceError("Распакованный ZIP превышает допустимый размер")
        return entries

    @staticmethod
    def _safe_relative(name: str) -> Path:
        normalized = name.replace("\\", "/")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or any(part == "" for part in path.parts[:-1]):
            raise WorkspaceError(f"Небезопасный путь в ZIP: {name}")
        return Path(*path.parts)

    @staticmethod
    def _validate_id(value: str) -> None:
        if not WORKSPACE_ID.fullmatch(value or ""):
            raise WorkspaceError("Идентификатор должен быть snake_case/kebab-case длиной 2–64 символа")

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _write_manifest(target: Path, manifest: WorkspaceManifest) -> None:
        (target / "workspace.json").write_text(json.dumps(asdict(manifest), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _read_manifest(target: Path) -> WorkspaceManifest:
        return WorkspaceManifest(**json.loads((target / "workspace.json").read_text(encoding="utf-8")))

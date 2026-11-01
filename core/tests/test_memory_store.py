import json

import pytest

from core.memory_store import LocalMemoryStore, MemoryKind, MemorySafetyError


def test_memory_is_partitioned_searchable_exportable_and_deletable(tmp_path):
    store = LocalMemoryStore(tmp_path / "memory")
    record = store.append(MemoryKind.KNOWLEDGE, "Palm audience prefers short video", {"source": "research"})
    store.append(MemoryKind.PREFERENCES, "Prefer concise reports")

    assert [item.record_id for item in store.search("short video")] == [record.record_id]
    assert len(store.export(MemoryKind.KNOWLEDGE)) == 1
    exported = store.export_to(tmp_path / "exports" / "memory.json")
    assert json.loads(exported.read_text(encoding="utf-8"))[0]["kind"] == "knowledge"
    assert store.delete(record.record_id) is True
    assert store.search("short video") == []


def test_memory_rejects_secret_like_fields_and_values(tmp_path):
    store = LocalMemoryStore(tmp_path / "memory")
    with pytest.raises(MemorySafetyError):
        store.append(MemoryKind.KNOWLEDGE, "normal note", {"api_key": "must-not-store"})
    with pytest.raises(MemorySafetyError):
        store.append(MemoryKind.EVENTS, "Authorization bearer abcdefghijklmnop")

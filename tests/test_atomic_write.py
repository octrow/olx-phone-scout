"""Atomic JSON writes: a failed write must leave the previous file intact."""

import json
from pathlib import Path

import pytest

from src.infrastructure.atomic import write_json_atomic


def test_writes_json(tmp_path: Path):
    target = tmp_path / "a.json"
    write_json_atomic(target, {"x": "привет"}, indent=2)
    assert json.loads(target.read_text(encoding="utf-8")) == {"x": "привет"}
    assert list(tmp_path.iterdir()) == [target]


def test_failed_serialization_keeps_old_file(tmp_path: Path):
    target = tmp_path / "a.json"
    target.write_text('{"old": 1}', encoding="utf-8")
    with pytest.raises(TypeError):
        write_json_atomic(target, {"bad": object()})
    assert json.loads(target.read_text(encoding="utf-8")) == {"old": 1}
    assert list(tmp_path.iterdir()) == [target]


def test_cache_save_is_atomic(tmp_path: Path, monkeypatch):
    from unittest.mock import MagicMock

    from src.infrastructure.cache import CustomCache

    cache_file = tmp_path / "c.json"
    cache_file.write_text('{"k": "v"}', encoding="utf-8")
    cache = CustomCache(cache_file, MagicMock())
    cache.cache["bad"] = object()
    cache.save()  # error is logged, not raised
    assert json.loads(cache_file.read_text(encoding="utf-8")) == {"k": "v"}

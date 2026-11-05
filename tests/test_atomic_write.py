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


def test_recategorize_failure_keeps_all_listings(tmp_path: Path, monkeypatch):
    """Step 2 rewrites all_listings.json; a failed dump must not truncate it."""
    import main

    files = {
        name: tmp_path / f"{name}.json"
        for name in ("all_listings", "iphones", "androids", "unknown")
    }
    original = {"total": 1, "scraped_at": "t", "listings": [{"title": "Redmi 9", "link": "a"}]}
    files["all_listings"].write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setattr(main.config, "get_output_files", lambda: files)
    monkeypatch.setattr(main, "detect_phone_brand_improved", lambda _t: (object(), "android"))

    main.run_recategorization()  # the error is logged, not raised

    assert json.loads(files["all_listings"].read_text(encoding="utf-8")) == original

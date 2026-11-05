"""Kimovil (brand, model) parsing: a sub-brand in the title wins over its parent brand."""

import pytest

from src.enrichment.spec_enrichment import SpecEnricher


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Xiaomi Redmi Note 12 Pro 8/256", ("Redmi", "Note 12 Pro")),
        ("Xiaomi Poco X5 Pro", ("Poco", "X5 Pro")),
        ("Xiaomi Redmi 12C", ("Redmi", "12C")),
        ("Xiaomi 13 Pro", ("Xiaomi", "13 Pro")),
    ],
)
def test_sub_brand_wins_over_xiaomi(tmp_path, title, expected):
    enricher = SpecEnricher(cache_db=str(tmp_path / "specs.db"))

    assert enricher.extract_brand_and_model(title) == expected

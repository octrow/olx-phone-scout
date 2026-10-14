"""Tests for SpecEnricher and title brand/model extraction"""

import pytest

from src.enrichment.spec_enrichment import SpecEnricher


@pytest.fixture
def enricher():
    """Create a SpecEnricher for testing brand/model extraction without DB overhead"""
    instance = SpecEnricher.__new__(SpecEnricher)
    instance.scraper = None
    return instance


class TestSpecEnricherExtractBrandAndModel:
    """Test SpecEnricher.extract_brand_and_model() on various listing titles"""

    def test_samsung_title(self, enricher):
        """Standard Samsung title with model and storage"""
        result = enricher.extract_brand_and_model("Samsung s23 Ultra 256")
        assert result == ("Samsung", "Galaxy S23 Ultra")

    def test_pixel_title_with_cyrillic_suffix(self, enricher):
        """Pixel title with storage and Cyrillic suffix 'без торга'"""
        result = enricher.extract_brand_and_model("Pixel 9 pro xl 12/128gb gray без торга")
        assert result == ("Google", "Pixel 9 Pro")

    def test_cyrillic_samsung_title_returns_none(self, enricher):
        """Cyrillic brand 'Самсунг' is not yet in BRAND_ALIASES, returns None"""
        result = enricher.extract_brand_and_model("Самсунг с23 ультра Торг есть")
        assert result is None

    def test_misspelled_xiaomi_title_returns_none(self, enricher):
        """Typo 'Xioami' is not yet in BRAND_ALIASES, returns None"""
        result = enricher.extract_brand_and_model("Xioami 14 , 512/16")
        assert result is None

    def test_non_phone_title_returns_none(self, enricher):
        """Title with no recognizable phone returns None"""
        result = enricher.extract_brand_and_model("Продам чехол на диван")
        assert result is None

    def test_empty_title_returns_none(self, enricher):
        """Empty string returns None"""
        result = enricher.extract_brand_and_model("")
        assert result is None

    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("OnePlus 12 16/512", ("Oneplus", "12")),
            ("Xiaomi 12 Pro 256GB", ("Xiaomi", "12 Pro")),
            ("Redmi Note 13", ("Redmi", "Note 13")),
            ("POCO X6 Pro 5G", ("Poco", "X6 Pro")),
        ],
    )
    def test_additional_phone_brands(self, enricher, title, expected):
        """Verify brand and model extraction for other supported brands"""
        assert enricher.extract_brand_and_model(title) == expected

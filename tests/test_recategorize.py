import json

import pytest

from src.detection import recategorize


@pytest.fixture
def results_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(recategorize, "get_results_dir", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def fake_detect(monkeypatch):
    table = {
        "iPhone 13 128GB": ("apple", "iphone", 90),
        "Samsung A54": ("samsung", "android", 80),
        "Xiaomi 14": ("xiaomi", "android", 70),
    }
    monkeypatch.setattr(
        recategorize, "detect_phone_brand", lambda text: table.get(text, ("unknown", "unknown", 0))
    )


def _listing(title, price=1000):
    return {"title": title, "price": price, "link": f"https://olx.kz/{title.replace(' ', '-')}"}


def _write_input(directory, listings, scraped_at="2025-01-14T12:00:00"):
    (directory / "all_listings.json").write_text(
        json.dumps({"total": len(listings), "scraped_at": scraped_at, "listings": listings}),
        encoding="utf-8",
    )


def _read(directory, name):
    return json.loads((directory / name).read_text(encoding="utf-8"))


class TestDetectPhoneBrandImproved:
    def test_drops_score_from_result(self, fake_detect):
        assert recategorize.detect_phone_brand_improved("iPhone 13 128GB") == ("apple", "iphone")

    def test_real_detection_of_samsung(self):
        brand, phone_type = recategorize.detect_phone_brand_improved(
            "Samsung Galaxy S24 Ultra 256GB"
        )
        assert brand == "samsung"
        assert phone_type == "android"


class TestMain:
    def test_missing_input_file_writes_nothing(self, results_dir):
        assert recategorize.main() is None
        assert list(results_dir.iterdir()) == []

    def test_splits_listings_into_files(self, results_dir, fake_detect):
        _write_input(
            results_dir,
            [
                _listing("iPhone 13 128GB"),
                _listing("Samsung A54"),
                _listing("Xiaomi 14"),
                _listing("Nokia 3310"),
            ],
        )

        recategorize.main()

        iphones = _read(results_dir, "iphones.json")
        androids = _read(results_dir, "androids.json")
        unknown = _read(results_dir, "unknown.json")
        assert iphones["count"] == 1
        assert [p["title"] for p in iphones["phones"]] == ["iPhone 13 128GB"]
        assert androids["count"] == 2
        assert [p["detected_brand"] for p in androids["phones"]] == ["samsung", "xiaomi"]
        assert unknown["count"] == 1
        assert unknown["phones"][0]["phone_type"] == "unknown"

    def test_all_listings_updated_and_metadata_kept(self, results_dir, fake_detect):
        _write_input(
            results_dir,
            [_listing("iPhone 13 128GB"), _listing("Nokia 3310")],
            scraped_at="2025-02-01T08:00:00",
        )

        recategorize.main()

        saved = _read(results_dir, "all_listings.json")
        assert saved["total"] == 2
        assert saved["scraped_at"] == "2025-02-01T08:00:00"
        assert [(x["detected_brand"], x["phone_type"]) for x in saved["listings"]] == [
            ("apple", "iphone"),
            ("unknown", "unknown"),
        ]

    def test_overwrites_stale_categorization(self, results_dir, fake_detect):
        stale = _listing("Samsung A54")
        stale["detected_brand"] = "apple"
        stale["phone_type"] = "iphone"
        _write_input(results_dir, [stale])

        recategorize.main()

        assert _read(results_dir, "iphones.json") == {"count": 0, "phones": []}
        androids = _read(results_dir, "androids.json")
        assert androids["phones"][0]["detected_brand"] == "samsung"

    def test_non_ascii_titles_written_unescaped(self, results_dir, fake_detect):
        _write_input(results_dir, [_listing("Телефон Нокиа")])

        recategorize.main()

        assert "Телефон Нокиа" in (results_dir / "unknown.json").read_text(encoding="utf-8")

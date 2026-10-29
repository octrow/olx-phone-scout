import asyncio
import sqlite3

import pytest
from curl_cffi import CurlError

from src.enrichment import kimovil_scraper
from src.enrichment.kimovil_scraper import KimovilScraper

PAGE = """
<html><body>
<h1> Samsung Galaxy S24 Ultra </h1>
<table>
<tr><th>Size</th><td>79.0 mm x 162.3 mm x 8.6 mm</td></tr>
<tr><td>Weight</td><td>232 g</td></tr>
<tr><td>Diagonal</td><td>6.8"</td></tr>
<tr><td>Type</td><td>Dynamic AMOLED 2X</td></tr>
<tr><td>Resolution</td><td>1440 x 3120 px QHD+</td></tr>
<tr><td>Density</td><td>505 ppi</td></tr>
<tr><td>Others</td><td>Refresh rate 120 Hz</td></tr>
<tr><td>Frequency</td><td>3.3 GHz</td></tr>
<tr><td>Nanometer</td><td>4 nm</td></tr>
<tr><td>RAM</td><td>12 GB</td></tr>
<tr><td>Score</td><td>1,814,869</td></tr>
<tr><td>Capacity</td><td>256 GB</td></tr>
<tr><td>Resolution</td><td>200 Mpx</td></tr>
<tr><td>Sensor</td><td>ISOCELL HP2</td></tr>
<tr><td>Fingerprint</td><td>Yes</td></tr>
<tr><td>Capacity</td><td>5000 mAh</td></tr>
<tr><td>Fast charge</td><td>45 W</td></tr>
<tr><td>Release date</td><td>January 2024</td></tr>
<tr><td>Launch price</td><td>€ 1,459.00 ($ 1,677.32)</td></tr>
<tr><td>Wireless Power</td><td>15 W</td></tr>
<tr><td>Same</td><td>Same</td></tr>
<tr><td>Empty</td><td></td></tr>
<tr><td>Lonely</td></tr>
</table>
<dl class="dxomark-scores-dl"><dd>150 points</dd></dl>
</body></html>
"""


@pytest.fixture
def scraper(tmp_path):
    s = KimovilScraper(cache_db=str(tmp_path / "specs.db"))
    s.min_delay = 0
    return s


class _Response:
    def __init__(self, status_code=200, text="", url="https://final.test/p", headers=None):
        self.status_code = status_code
        self.text = text
        self.url = url
        self.headers = headers or {}


def _session_returning(response=None, error=None):
    class _Session:
        def __init__(self, impersonate):
            self.impersonate = impersonate

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, timeout):
            if error:
                raise error
            return response

    return _Session


def test_init_creates_cache_db_in_missing_parent_dir(tmp_path):
    db = tmp_path / "nested" / "dir" / "specs.db"
    KimovilScraper(cache_db=str(db))
    assert db.exists()


@pytest.mark.parametrize(
    ("brand", "model", "expected"),
    [
        ("Samsung", "Galaxy S24 Ultra", "samsung-galaxy-s24-ultra"),
        ("Xiaomi", "Redmi Note 12+", "xiaomi-redmi-note-12-plus"),
        ("Google", "Pixel 9 (Pro)", "google-pixel-9-pro"),
        ("Honor", "Magic 6/Pro", "honor-magic-6-pro"),
    ],
)
def test_normalize_model_name(scraper, brand, model, expected):
    assert scraper._normalize_model_name(brand, model) == expected


def test_build_url(scraper):
    assert (
        scraper._build_kimovil_url("Samsung", "Galaxy S24")
        == "https://www.kimovil.com/en/where-to-buy-samsung-galaxy-s24"
    )


def test_cache_roundtrip_and_unknown_key(scraper):
    specs = {"a": 1, "b": None, "c": "x"}
    scraper._save_to_cache("k", "Brand", "Model", specs)
    assert scraper._get_cached_specs("k") == specs
    assert scraper._get_cached_specs("other") is None
    with sqlite3.connect(scraper.cache_db) as conn:
        count = conn.execute("SELECT field_count FROM phone_specs").fetchone()[0]
    assert count == 2


def test_failed_cache_entries_are_not_served(scraper):
    scraper._save_to_cache("k", "Brand", "Model", {"a": 1}, success=False)
    assert scraper._get_cached_specs("k") is None


def test_cache_errors_are_swallowed(scraper):
    with sqlite3.connect(scraper.cache_db) as conn:
        conn.execute("DROP TABLE phone_specs")
    assert scraper._get_cached_specs("k") is None
    scraper._save_to_cache("k", "B", "M", {"a": 1})


def test_parse_page_extracts_typed_specs(scraper):
    specs = scraper._parse_page(PAGE, "https://final.test/p", "Samsung", "S24 Ultra")

    assert specs["brand"] == "Samsung"
    assert specs["model"] == "S24 Ultra"
    assert specs["kimovil_url"] == "https://final.test/p"
    assert specs["full_name"] == "Samsung Galaxy S24 Ultra"
    assert specs["weight"] == 232
    assert (specs["size_width"], specs["size_height"], specs["size_depth"]) == (79.0, 162.3, 8.6)
    assert specs["screen_diagonal"] == 6.8
    assert specs["screen_type"] == "Dynamic AMOLED 2X"
    assert specs["screen_type_detail"] == "AMOLED"
    assert specs["screen_resolution_width"] == 1440
    assert specs["screen_resolution_height"] == 3120
    assert specs["screen_resolution_name"] == "QHD+"
    assert specs["screen_density"] == 505
    assert specs["screen_refresh_rate"] == 120
    assert specs["processor_frequency"] == 3.3
    assert specs["processor_nm"] == 4
    assert specs["ram_size"] == 12
    assert specs["antutu_v10_score"] == 1814869
    assert specs["storage_capacity"] == 256
    assert specs["battery_capacity"] == 5000
    assert specs["camera_main_resolution"] == 200
    assert specs["camera_main_sensor"] == "ISOCELL HP2"
    assert specs["fingerprint"] is True
    assert specs["fast_charging_wattage"] == 45
    assert specs["release_year"] == 2024
    assert specs["release_month"] == 1
    assert specs["launch_price_eur"] == 1459.0
    assert specs["launch_price_usd"] == 1677.32
    assert specs["dxomark_score"] == 150
    assert specs["extra_wireless_power"] == "15 W"


def test_parse_page_skips_degenerate_rows(scraper):
    specs = scraper._parse_page(PAGE, "u", "Samsung", "S24 Ultra")
    assert "extra_same" not in specs
    assert "extra_empty" not in specs
    assert "extra_lonely" not in specs


def test_parse_page_without_h1_falls_back_to_brand_and_model(scraper):
    html = "<html><body><table><tr><td>RAM</td><td>8 GB</td></tr></table></body></html>"
    specs = scraper._parse_page(html, "u", "Xiaomi", "14")
    assert specs["full_name"] == "Xiaomi 14"
    assert specs["ram_size"] == 8
    assert "dxomark_score" not in specs


def test_first_label_wins_for_repeated_rows(scraper):
    rows = [("Type", "IPS LCD"), ("Type", "OLED")]
    assert scraper._table_specs(rows) == {"screen_type": "IPS LCD"}


def test_capacity_label_is_battery_only_with_mah(scraper):
    assert scraper._spec_key("Capacity", "4500 mAh") == "battery_capacity"
    assert scraper._spec_key("Capacity", "128 GB") == "storage_capacity_raw"
    assert scraper._spec_key("Some Thing (x)", "v") == "extra_some_thing_x"


def test_convert_booleans_and_empty_values(scraper):
    out = scraper._parse_and_convert_types(
        {"a": "Yes", "b": "no", "c": "--", "d": "", "e": None, "f": 5, "g": "  text  "}
    )
    assert out == {"a": True, "b": False, "c": None, "d": None, "e": None, "f": 5, "g": "text"}


def test_convert_keeps_raw_string_when_pattern_does_not_match(scraper):
    out = scraper._parse_and_convert_types(
        {"weight_raw": "heavy", "ram_size_raw": "unknown", "fast_charge": "Yes, fast"}
    )
    assert out["weight_raw"] == "heavy"
    assert out["ram_size_raw"] == "unknown"
    assert out["fast_charge"] == "Yes, fast"


def test_convert_release_date_without_month(scraper):
    out = scraper._parse_and_convert_types({"release_date": "2023"})
    assert out["release_year"] == 2023
    assert "release_month" not in out
    assert out["release_date"] == "2023"


def test_convert_fast_charge_rounds_watts(scraper):
    out = scraper._parse_and_convert_types({"fast_charge": "67.5 W"})
    assert out["fast_charging_wattage"] == 68


def test_convert_launch_price_only_usd(scraper):
    out = scraper._parse_and_convert_types({"launch_price": "$ 999.00"})
    assert out == {"launch_price_usd": 999.0}


def test_fetch_html_success(scraper, monkeypatch):
    resp = _Response(text="<html></html>", url="https://final.test/redirected")
    monkeypatch.setattr(kimovil_scraper, "AsyncSession", _session_returning(resp))
    url, html = asyncio.run(scraper._fetch_html("https://start.test"))
    assert url == "https://final.test/redirected"
    assert html == "<html></html>"


def test_fetch_html_network_error(scraper, monkeypatch):
    monkeypatch.setattr(
        kimovil_scraper, "AsyncSession", _session_returning(error=CurlError("boom"))
    )
    assert asyncio.run(scraper._fetch_html("https://start.test")) == ("https://start.test", None)


def test_scrape_page_parses_fetched_html(scraper, monkeypatch):
    resp = _Response(text=PAGE)
    monkeypatch.setattr(kimovil_scraper, "AsyncSession", _session_returning(resp))
    specs = asyncio.run(scraper._scrape_page("https://start.test", "Samsung", "S24 Ultra"))
    assert specs["kimovil_url"] == "https://final.test/p"
    assert specs["ram_size"] == 12


def test_scrape_phone_specs_cache_hit_skips_network(scraper):
    scraper._save_to_cache("samsung_galaxy_s24", "Samsung", "Galaxy S24", {"ram_size": 8})

    async def boom(*args):
        raise AssertionError("should not fetch")

    scraper._scrape_page = boom
    result = asyncio.run(scraper.scrape_phone_specs("Samsung", "Galaxy S24"))
    assert result == {"ram_size": 8}


def test_scrape_phone_specs_caches_meaningful_result(scraper):
    specs = {"brand": "A", "model": "B", "x": 1, "y": 2, "z": None}
    calls = []

    async def fake(url, brand, model):
        calls.append(url)
        return specs

    scraper._scrape_page = fake
    first = asyncio.run(scraper.scrape_phone_specs("A", "B"))
    second = asyncio.run(scraper.scrape_phone_specs("A", "B"))

    assert first == specs
    assert second == specs
    assert len(calls) == 1
    assert calls[0].endswith("where-to-buy-a-b")


@pytest.mark.parametrize("result", [None, {"brand": "A", "model": "B", "x": 1}])
def test_scrape_phone_specs_records_failure_without_serving_it(scraper, result):
    async def fake(url, brand, model):
        return result

    scraper._scrape_page = fake
    out = asyncio.run(scraper.scrape_phone_specs("A", "B"))

    assert out == result
    assert scraper._get_cached_specs("a_b") is None
    with sqlite3.connect(scraper.cache_db) as conn:
        row = conn.execute("SELECT success FROM phone_specs WHERE model_key = 'a_b'").fetchone()
    assert row == (0,)


def test_scrape_batch_maps_results_and_exceptions(scraper):
    async def fake(brand, model):
        if model == "bad":
            raise RuntimeError("nope")
        if model == "none":
            return None
        return {"model": model}

    scraper.scrape_phone_specs = fake
    phones = [("A", "ok"), ("A", "bad"), ("A", "none")]
    out = asyncio.run(scraper.scrape_batch(phones, max_concurrent=1))
    assert out == [{"model": "ok"}, None, None]

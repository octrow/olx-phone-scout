"""Tests for async OLX scraper"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from market_sources.polite_http import PoliteClient

from src.core.async_scraper import AsyncOLXScraper


@pytest.mark.asyncio
class TestAsyncOLXScraperInit:
    """Test AsyncOLXScraper initialization"""

    async def test_init_creates_scraper(self):
        """Init creates scraper with correct attributes"""
        scraper = AsyncOLXScraper()
        assert scraper.base_url
        assert scraper.headers
        assert scraper.listings == []
        assert scraper.seen_links == set()
        assert scraper.client is None

    async def test_context_manager_enter(self):
        """Context manager enter creates HTTP client"""
        scraper = AsyncOLXScraper()
        async with scraper:
            assert scraper.client is not None
            assert isinstance(scraper.client, PoliteClient)

    async def test_context_manager_exit(self):
        """Context manager exit closes HTTP client"""
        scraper = AsyncOLXScraper()
        async with scraper:
            client = scraper.client
            client.aclose = AsyncMock(wraps=client.aclose)
        client.aclose.assert_awaited_once()


@pytest.mark.asyncio
class TestAsyncOLXScraperMethods:
    """Test AsyncOLXScraper methods"""

    async def test_detect_phone_brand(self):
        """detect_phone_brand identifies brand"""
        scraper = AsyncOLXScraper()

        test_cases = [
            ("Samsung S24", "samsung"),
            ("iPhone 15 Pro", "iphone"),
            ("Xiaomi 14", "xiaomi"),
        ]

        for title, expected_brand in test_cases:
            brand, _phone_type, confidence = scraper.detect_phone_brand(title)
            assert brand == expected_brand
            assert confidence > 0

    async def test_setup_scrape_params(self):
        """_setup_scrape_params creates params dict"""
        scraper = AsyncOLXScraper()
        params = scraper._setup_scrape_params(
            min_price=100000, max_price=300000, max_pages=10, days_back=30
        )

        assert isinstance(params, dict)
        assert params["min_price"] == 100000
        assert params["max_price"] == 300000
        assert params["max_pages"] == 10

    async def test_build_search_params(self):
        """_build_search_params creates URL params"""
        scraper = AsyncOLXScraper()
        params = scraper._build_search_params(min_price=100000, max_price=300000, page=2)

        assert isinstance(params, dict)
        assert "search[filter_float_price:from]" in params
        assert params["search[filter_float_price:from]"] == "100000"

    async def test_extract_card_link(self):
        """_extract_card_link extracts link from card"""
        scraper = AsyncOLXScraper()

        from bs4 import BeautifulSoup

        html = '<div><a href="/listing/12345"></a></div>'
        card = BeautifulSoup(html, "html.parser")

        link = scraper._extract_card_link(card)
        assert link is not None
        assert "listing/12345" in link

    async def test_extract_card_title(self):
        """_extract_card_title extracts title"""
        scraper = AsyncOLXScraper()

        from bs4 import BeautifulSoup

        html = "<div><h6>Samsung S24 Ultra</h6></div>"
        card = BeautifulSoup(html, "html.parser")

        title = scraper._extract_card_title(card)
        assert title == "Samsung S24 Ultra"

    async def test_extract_card_price(self):
        """_extract_card_price extracts price"""
        scraper = AsyncOLXScraper()

        from bs4 import BeautifulSoup

        html = '<div><p data-testid="ad-price">250000 ₸</p></div>'
        card = BeautifulSoup(html, "html.parser")

        price = scraper._extract_card_price(card)
        assert price == 250000

    async def test_extract_price_various_formats(self):
        """_extract_price handles various formats"""
        scraper = AsyncOLXScraper()

        test_cases = [
            ("250 000 ₸", 250000),
            ("250000 ₸", 250000),
            ("250 тг", 250),
            ("Free", 0),
        ]

        for price_text, expected in test_cases:
            result = scraper._extract_price(price_text)
            assert result == expected

    async def test_detect_card_status(self):
        """_detect_card_status detects phone status"""
        scraper = AsyncOLXScraper()

        test_cases = [
            ("Новый Samsung S24", "Новый"),
            ("Б/у iPhone 15", "Б/у"),
            ("Samsung S24", "Б/у"),
        ]

        for title, expected in test_cases:
            status = scraper._detect_card_status(title)
            assert status == expected

    async def test_scrape_listing_cards_success(self):
        """scrape_listing_cards fetches pages"""
        scraper = AsyncOLXScraper()

        mock_html = """
        <html>
            <div data-cy="l-card">
                <a href="/listing/1"></a>
                <h6>Samsung S24</h6>
                <p data-testid="ad-price">250000 ₸</p>
            </div>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.status_code = 200

        async with scraper:
            scraper.client.get = AsyncMock(return_value=mock_response)

            result = await scraper.scrape_listing_cards(
                min_price=100000, max_price=300000, max_pages=1, days_back=30
            )

            assert isinstance(result, list)

    def test_merge_with_existing_no_file(self):
        """merge_with_existing handles missing file"""
        scraper = AsyncOLXScraper()
        scraper.listings = [{"title": "Test", "link": "http://test.com/1"}]

        merged = scraper.merge_with_existing(existing_file=None, use_session_dir=False)

        assert len(merged) == 1
        assert merged[0]["title"] == "Test"

    async def test_extract_card_location(self):
        """_extract_card_location extracts location"""
        scraper = AsyncOLXScraper()

        from bs4 import BeautifulSoup

        html = '<div><p data-testid="location-date">Almaty, Kazakhstan</p></div>'
        card = BeautifulSoup(html, "html.parser")

        location = scraper._extract_card_location(card)
        assert location == "Almaty, Kazakhstan"

    async def test_extract_card_location_missing(self):
        """_extract_card_location handles missing location"""
        scraper = AsyncOLXScraper()

        from bs4 import BeautifulSoup

        html = "<div></div>"
        card = BeautifulSoup(html, "html.parser")

        location = scraper._extract_card_location(card)
        assert location == "N/A"

    async def test_extract_card_image(self):
        """_extract_card_image extracts image URL"""
        scraper = AsyncOLXScraper()

        from bs4 import BeautifulSoup

        html = '<div><img src="https://example.com/image.jpg" /></div>'
        card = BeautifulSoup(html, "html.parser")

        image_url = scraper._extract_card_image(card)
        assert image_url == "https://example.com/image.jpg"

    async def test_extract_card_image_missing(self):
        """_extract_card_image handles missing image"""
        scraper = AsyncOLXScraper()

        from bs4 import BeautifulSoup

        html = "<div></div>"
        card = BeautifulSoup(html, "html.parser")

        image_url = scraper._extract_card_image(card)
        assert image_url == ""

    async def test_extract_listing_card_complete(self):
        """_extract_listing_card extracts full card data"""
        scraper = AsyncOLXScraper()

        from bs4 import BeautifulSoup

        html = """
        <div data-cy="l-card">
            <a href="/listing/12345"></a>
            <h6>Samsung Galaxy S24 Ultra</h6>
            <p data-testid="ad-price">350000 ₸</p>
            <p data-testid="location-date">Almaty</p>
            <img src="https://example.com/phone.jpg" />
        </div>
        """
        card = BeautifulSoup(html, "html.parser")

        listing = scraper._extract_listing_card(card)

        assert listing is not None
        assert listing["title"] == "Samsung Galaxy S24 Ultra"
        assert listing["price"] == 350000
        assert listing["location"] == "Almaty"
        assert "listing/12345" in listing["link"]
        assert listing["detected_brand"] == "samsung"
        assert listing["phone_type"] == "android"
        assert listing["brand_confidence"] > 0

    async def test_extract_listing_card_no_link(self):
        """_extract_listing_card returns None without link"""
        scraper = AsyncOLXScraper()

        from bs4 import BeautifulSoup

        html = '<div data-cy="l-card"><h6>Test</h6></div>'
        card = BeautifulSoup(html, "html.parser")

        listing = scraper._extract_listing_card(card)
        assert listing is None

    async def test_process_page_cards(self):
        """_process_page_cards processes multiple cards"""
        scraper = AsyncOLXScraper()

        from bs4 import BeautifulSoup

        html1 = """
        <div data-cy="l-card">
            <a href="/listing/1"></a>
            <h6>Samsung S24</h6>
            <p data-testid="ad-price">250000 ₸</p>
        </div>
        """
        html2 = """
        <div data-cy="l-card">
            <a href="/listing/2"></a>
            <h6>iPhone 15</h6>
            <p data-testid="ad-price">450000 ₸</p>
        </div>
        """

        cards = [BeautifulSoup(html1, "html.parser"), BeautifulSoup(html2, "html.parser")]

        count = scraper._process_page_cards(cards)

        assert count == 2
        assert len(scraper.listings) == 2
        assert len(scraper.seen_links) == 2

    async def test_process_page_cards_deduplication(self):
        """_process_page_cards deduplicates cards"""
        scraper = AsyncOLXScraper()

        from bs4 import BeautifulSoup

        html = """
        <div data-cy="l-card">
            <a href="/listing/1"></a>
            <h6>Samsung S24</h6>
            <p data-testid="ad-price">250000 ₸</p>
        </div>
        """

        card = BeautifulSoup(html, "html.parser")
        cards = [card, card]  # Same card twice

        count = scraper._process_page_cards(cards)

        assert count == 1
        assert len(scraper.listings) == 1

    async def test_fetch_page_listings_no_client(self):
        """_fetch_page_listings raises without client"""
        scraper = AsyncOLXScraper()

        with pytest.raises(RuntimeError, match="Client not initialized"):
            await scraper._fetch_page_listings("https://test.com", {}, 1, 10)


class TestAsyncScraperSaveOperations:
    """Test save and merge operations"""

    def test_merge_with_existing_adds_new_listings(self):
        """merge_with_existing adds new listings to existing file"""
        import json
        import tempfile
        from pathlib import Path

        scraper = AsyncOLXScraper()
        scraper.listings = [
            {"link": "/new1", "title": "New Phone 1"},
            {"link": "/new2", "title": "New Phone 2"},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            existing_data = {"listings": [{"link": "/old1", "title": "Old Phone 1"}]}
            json.dump(existing_data, f)
            temp_file = f.name

        try:
            result = scraper.merge_with_existing(temp_file, use_session_dir=False)

            assert len(result) == 3
            assert any(item["link"] == "/old1" for item in result)
            assert any(item["link"] == "/new1" for item in result)
            assert any(item["link"] == "/new2" for item in result)
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_merge_with_existing_deduplicates(self):
        """merge_with_existing deduplicates by link"""
        import json
        import tempfile
        from pathlib import Path

        scraper = AsyncOLXScraper()
        scraper.listings = [
            {"link": "/dup", "title": "Duplicate Phone"},
            {"link": "/new", "title": "New Phone"},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            existing_data = {"listings": [{"link": "/dup", "title": "Duplicate Phone"}]}
            json.dump(existing_data, f)
            temp_file = f.name

        try:
            result = scraper.merge_with_existing(temp_file, use_session_dir=False)

            assert len(result) == 2  # Should not duplicate
            links = [item["link"] for item in result]
            assert links.count("/dup") == 1
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_merge_with_existing_logs_total_after_merge_once(self):
        """merge_with_existing logs 'Total after merge' once"""
        import json
        import tempfile
        from pathlib import Path

        from loguru import logger

        scraper = AsyncOLXScraper()
        scraper.listings = [{"link": "/new", "title": "New Phone"}]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            existing_data = {"listings": [{"link": "/old", "title": "Old Phone"}]}
            json.dump(existing_data, f)
            temp_file = f.name

        captured_messages = []
        handler_id = logger.add(lambda msg: captured_messages.append(str(msg)))

        try:
            result = scraper.merge_with_existing(temp_file, use_session_dir=False)

            assert len(result) == 2
            merge_logs = [msg for msg in captured_messages if "Total after merge" in msg]
            assert len(merge_logs) == 1
        finally:
            logger.remove(handler_id)
            Path(temp_file).unlink(missing_ok=True)

    def test_get_output_files_session_dir(self):
        """_get_output_files returns session directory paths"""
        from pathlib import Path

        scraper = AsyncOLXScraper()

        with patch("src.core.config.get_output_files") as mock_get:
            with patch("src.core.config.get_results_dir") as mock_results:
                with patch("src.core.config.get_session_name") as mock_session:
                    mock_get.return_value = {"all_listings": "/path/all.json"}
                    mock_results.return_value = Path("/results")
                    mock_session.return_value = "test_session"

                    files, results_dir = scraper._get_output_files(use_session_dir=True)

                    assert "all_listings" in files
                    assert results_dir == Path("/results")

    def test_get_output_files_legacy(self):
        """_get_output_files returns legacy paths"""

        scraper = AsyncOLXScraper()

        with patch("src.core.config.ALL_LISTINGS_FILE", "/legacy/all.json"):
            with patch("src.core.config.RESULTS_DIR", Path("/legacy")):
                files, _results_dir = scraper._get_output_files(use_session_dir=False)

                assert files["all_listings"] == "/legacy/all.json"
                assert "iphones" in files
                assert "androids" in files
                assert "unknown" in files

    def test_categorize_listings(self):
        """categorize_listings splits by phone type"""
        scraper = AsyncOLXScraper()

        all_listings = [
            {"title": "iPhone 15", "phone_type": "iphone"},
            {"title": "Samsung S24", "phone_type": "android"},
            {"title": "Random Phone", "phone_type": "unknown"},
            {"title": "iPhone 14", "phone_type": "iphone"},
            {"title": "Xiaomi 14", "phone_type": "android"},
        ]

        iphones, androids, unknown = scraper.categorize_listings(all_listings)

        assert len(iphones) == 2
        assert len(androids) == 2
        assert len(unknown) == 1

    def test_apply_phone_filter_both(self):
        """_apply_phone_filter with 'both' returns all"""

        scraper = AsyncOLXScraper()
        iphones = [{"title": "iPhone 15"}]
        androids = [{"title": "Samsung S24"}]

        with patch("src.core.config.PHONE_TYPE_FILTER", "both"):
            result_iphones, result_androids = scraper._apply_phone_filter(iphones, androids)

            assert result_iphones == iphones
            assert result_androids == androids

    def test_apply_phone_filter_iphone_only(self):
        """_apply_phone_filter with 'iphone' returns only iPhones"""

        scraper = AsyncOLXScraper()
        iphones = [{"title": "iPhone 15"}]
        androids = [{"title": "Samsung S24"}]

        with patch("src.core.config.PHONE_TYPE_FILTER", "iphone"):
            result_iphones, result_androids = scraper._apply_phone_filter(iphones, androids)

            assert result_iphones == iphones
            assert result_androids == []

    def test_apply_phone_filter_android_only(self):
        """_apply_phone_filter with 'android' returns only Androids"""

        scraper = AsyncOLXScraper()
        iphones = [{"title": "iPhone 15"}]
        androids = [{"title": "Samsung S24"}]

        with patch("src.core.config.PHONE_TYPE_FILTER", "android"):
            result_iphones, result_androids = scraper._apply_phone_filter(iphones, androids)

            assert result_iphones == []
            assert result_androids == androids

    def test_save_all_listings_creates_file(self):
        """_save_all_listings creates JSON file"""
        import json
        import tempfile
        from pathlib import Path

        scraper = AsyncOLXScraper()
        all_listings = [
            {"title": "Phone 1", "link": "/1"},
            {"title": "Phone 2", "link": "/2"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "all_listings.json"

            with patch("src.core.config.DATA_DIR", Path(tmpdir)):
                scraper._save_all_listings(all_listings, str(output_file))

                assert output_file.exists()

                with output_file.open() as f:
                    data = json.load(f)
                    assert data["total"] == 2
                    assert len(data["listings"]) == 2
                    assert "scraped_at" in data
                    assert data["scraper_mode"] == "async_concurrent"

    def test_save_categories_creates_files(self):
        """_save_categories creates iPhone/Android/Unknown files"""
        import json
        import tempfile
        from pathlib import Path

        scraper = AsyncOLXScraper()
        iphones = [{"title": "iPhone 15", "link": "/1"}]
        androids = [{"title": "Samsung S24", "link": "/2"}]
        unknown = [{"title": "Unknown Phone", "link": "/3"}]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_files = {
                "iphones": str(Path(tmpdir) / "iphones.json"),
                "androids": str(Path(tmpdir) / "androids.json"),
                "unknown": str(Path(tmpdir) / "unknown.json"),
            }

            with patch("src.core.config.DATA_DIR", Path(tmpdir)):
                scraper._save_categories(iphones, androids, unknown, output_files, tmpdir)

                # Check all files exist
                assert Path(output_files["iphones"]).exists()
                assert Path(output_files["androids"]).exists()
                assert Path(output_files["unknown"]).exists()

                # Verify content
                with open(output_files["iphones"]) as f:
                    data = json.load(f)
                    assert data["count"] == 1
                    assert len(data["phones"]) == 1

    def test_log_unknown_samples_with_unknowns(self):
        """_log_unknown_samples logs sample of unknowns"""
        scraper = AsyncOLXScraper()
        unknown = [
            {"title": "Unknown Phone 1", "price": 100000},
            {"title": "Unknown Phone 2", "price": 200000},
        ]

        # Should not raise
        scraper._log_unknown_samples(unknown)

    def test_log_unknown_samples_empty(self):
        """_log_unknown_samples handles empty list"""
        scraper = AsyncOLXScraper()
        unknown = []

        # Should not raise
        scraper._log_unknown_samples(unknown)

    def test_log_scrape_start(self):
        """_log_scrape_start logs configuration"""
        scraper = AsyncOLXScraper()
        params = {"min_price": 100000, "max_price": 500000, "max_pages": 10, "days_back": 30}

        # Should not raise
        scraper._log_scrape_start(params)

    def test_save_results_integration(self):
        """save_results full workflow"""
        import tempfile
        from pathlib import Path

        scraper = AsyncOLXScraper()
        all_listings = [
            {"title": "iPhone 15", "phone_type": "iphone", "link": "/1", "price": 400000},
            {"title": "Samsung S24", "phone_type": "android", "link": "/2", "price": 300000},
            {"title": "Unknown", "phone_type": "unknown", "link": "/3", "price": 100000},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            output_files = {
                "all_listings": tmpdir_path / "all.json",
                "iphones": tmpdir_path / "iphones.json",
                "androids": tmpdir_path / "androids.json",
                "unknown": tmpdir_path / "unknown.json",
            }

            with patch("src.core.config.DATA_DIR", tmpdir_path):
                with patch("src.core.config.PHONE_TYPE_FILTER", "both"):
                    with patch("src.core.config.ALL_LISTINGS_FILE", output_files["all_listings"]):
                        with patch("src.core.config.IPHONES_FILE", output_files["iphones"]):
                            with patch("src.core.config.ANDROIDS_FILE", output_files["androids"]):
                                with patch("src.core.config.UNKNOWN_FILE", output_files["unknown"]):
                                    with patch("src.core.config.RESULTS_DIR", tmpdir_path):
                                        iphones, androids, unknown = scraper.save_results(
                                            all_listings, use_session_dir=False
                                        )

                                        # Verify returned data
                                        assert len(iphones) == 1
                                        assert len(androids) == 1
                                        assert len(unknown) == 1

                                        # Verify files created
                                        assert output_files["all_listings"].exists()
                                        assert output_files["iphones"].exists()
                                        assert output_files["androids"].exists()
                                        assert output_files["unknown"].exists()

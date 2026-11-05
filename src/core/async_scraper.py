#!/usr/bin/env python3
"""
ASYNC OLX Scraper - 10-30x FASTER! 🚀
======================================
Async implementation using httpx for concurrent page scraping.

Key improvements over sync version:
- Concurrent page fetching with asyncio.gather
- Persistent HTTP client (connection pooling)
- 10-30x faster for multi-page scrapes
- Same features: typo tolerance, fuzzy matching, brand detection

Performance:
- Sync version: ~15 pages in ~30 seconds (sequential)
- Async version: ~15 pages in ~3-5 seconds (concurrent)
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from httpx import HTTPStatusError, RequestError
from market_sources.polite_http import PoliteClient
from tqdm.asyncio import tqdm_asyncio

from src.core import config
from src.core.browser_transport import BrowserTransport
from src.detection.patterns import BRAND_PATTERNS, detect_phone_brand
from src.infrastructure.atomic import write_json_atomic
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

# OLX listing pages are HTML, not JSON (PoliteClient's default accept is JSON).
ACCEPT_HTML = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
ACCEPT_LANGUAGE = "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
# Same schedule the hand-rolled loop used: 0.5 * 2**attempt, now jittered + Retry-After aware.
MAX_RETRIES = 2
BACKOFF_BASE_S = 0.5
# OLX returns at most 1000 results (25 pages) per search; bigger price ranges get split.
OLX_RESULT_CAP = 1000
MIN_PRICE_SLICE_KZT = 1000
_STATE_RE = re.compile(r'window\.__PRERENDERED_STATE__\s*=\s*"(.*?)";\s*\n', re.S)


_AD_ID_RE = re.compile(r"-(ID\w+)\.html")


def _prerendered_state(html: str) -> dict | None:
    match = _STATE_RE.search(html)
    if not match:
        return None
    try:
        return json.loads(json.loads(f'"{match.group(1)}"'))
    except ValueError:
        return None


def ad_id(link: str) -> str | None:
    """OLX ad id ("IDr8vab") from a listing URL, ignoring query strings."""
    match = _AD_ID_RE.search(link)
    return match.group(1) if match else None


def parse_ad_meta(html: str) -> dict[str, dict]:
    """Seller type and city per ad id; HTML cards don't carry either."""
    state = _prerendered_state(html) or {}
    ads = state.get("listing", {}).get("listing", {}).get("ads", [])
    meta = {}
    for ad in ads:
        key = ad_id(ad.get("url", ""))
        if key:
            meta[key] = {
                "is_business": bool(ad.get("isBusiness")),
                "city": (ad.get("location") or {}).get("cityName"),
            }
    return meta


def parse_listing_totals(html: str) -> tuple[int, int] | None:
    """(total results, total pages) from an OLX search page, or None if the state blob is missing."""
    state = _prerendered_state(html)
    try:
        listing = state["listing"]["listing"]  # type: ignore[index]
        return int(listing["totalElements"]), int(listing["totalPages"])
    except (KeyError, TypeError, ValueError):
        return None


class AsyncOLXScraper:
    """Async scraper with concurrent page fetching - 10-30x faster!"""

    def __init__(self):
        self.base_url = config.OLX_BASE_URL
        self.headers = {
            "user-agent": config.USER_AGENT,
            "accept": ACCEPT_HTML,
            "accept-language": ACCEPT_LANGUAGE,
        }
        self.listings = []
        self.seen_links = set()  # Deduplicate
        self.client: PoliteClient | None = None
        self.ad_meta: dict[str, dict] = {}  # ad id -> {is_business, city}
        logger.info("Async scraper initialized")
        # Use centralized brand patterns
        self.brand_patterns = BRAND_PATTERNS
        logger.debug(f"Loaded {len(self.brand_patterns)} brand patterns")

    def _build_client(self) -> PoliteClient:
        """Shared polite HTTP transport (semaphore + pacing + retry/backoff)."""
        return PoliteClient(
            user_agent=config.USER_AGENT,
            headers={"accept": ACCEPT_HTML, "accept-language": ACCEPT_LANGUAGE},
            max_concurrency=config.ASYNC_MAX_CONCURRENCY or 10,
            min_delay_s=config.REQUEST_DELAY / 2,
            max_delay_s=config.REQUEST_DELAY,
            timeout_s=config.REQUEST_TIMEOUT,
            max_retries=MAX_RETRIES,
            backoff_base_s=BACKOFF_BASE_S,
            transport=BrowserTransport(),
        )

    async def __aenter__(self):
        """Initialize persistent HTTP client"""
        self.client = self._build_client()
        logger.info("✅ Async HTTP client started (PoliteClient: paced + retrying)")
        return self

    async def __aexit__(self, *_args):
        """Cleanup HTTP client"""
        if self.client:
            await self.client.aclose()
            logger.info("🔌 Async HTTP client closed")

    def detect_phone_brand(self, text):
        """
        Detect phone brand with fuzzy matching and typo tolerance
        Returns: (brand_name, phone_type, confidence_score)
        """
        brand, phone_type, score = detect_phone_brand(text)

        if brand != "unknown":
            logger.debug(f"Detected brand: {brand} (confidence: {score})")

        return brand, phone_type, score

    def _setup_scrape_params(self, min_price, max_price, max_pages, days_back):
        """Setup and validate scraping parameters"""
        return {
            "min_price": min_price or config.MIN_PRICE,
            "max_price": max_price or config.MAX_PRICE,
            "max_pages": max_pages or config.MAX_PAGES,
            "days_back": days_back or config.DAYS_BACK,
        }

    def _log_scrape_start(self, params: dict) -> None:
        """Log scraping configuration"""
        logger.info("=" * 80)
        logger.info("ASYNC SCRAPER - CONCURRENT PAGE FETCHING 🚀")
        logger.info("=" * 80)

        location_name = config.AVAILABLE_LOCATIONS.get(config.LOCATION, config.LOCATION)
        logger.info(
            f"🎯 Target: Phones in {location_name}, {params['min_price']:,} - {params['max_price']:,} KZT"
        )
        logger.info(
            f"📅 Timeline: Last {params['days_back']} days | Max pages: {params['max_pages']}"
        )
        logger.info("⚡ Mode: CONCURRENT (all pages fetched simultaneously)")

        logger.info(f"Location: {location_name}")
        logger.info(f"Min Price: {params['min_price']:,} KZT")
        logger.info(f"Max Price: {params['max_price']:,} KZT")
        logger.info(f"Max Pages: {params['max_pages']}")
        logger.info(f"Days Back: {params['days_back']}")
        logger.info("Mode: ASYNC CONCURRENT")

    def _build_search_params(self, min_price: int, max_price: int, page: int) -> dict:
        """Build search parameters for API request"""
        params = config.SEARCH_PARAMS.copy()
        if config.INCLUDE_BUSINESS:
            params.pop("search[private_business]", None)
        params.update(
            {
                "search[filter_float_price:from]": str(min_price),
                "search[filter_float_price:to]": str(max_price),
                "page": str(page),
            }
        )
        return params

    async def _fetch_page_listings(
        self, url: str, params: dict, page: int, max_pages: int
    ) -> list | Exception | None:
        """Fetch and parse listing cards from a single page (async).

        Concurrency capping, inter-request pacing and retry/backoff (429/5xx +
        transport errors, honoring ``Retry-After``) all live in ``PoliteClient``.
        Failures are still *returned* rather than raised, so one dead page never
        aborts the whole ``gather``.
        """
        if not self.client:
            raise RuntimeError("Client not initialized - use 'async with' context manager")

        logger.debug(f"📄 Fetching page {page}/{max_pages}...")
        try:
            response = await self.client.get(url, params=params)
            self.ad_meta.update(parse_ad_meta(response.text))
            soup = BeautifulSoup(response.content, "html.parser")
            return soup.find_all("div", {"data-cy": "l-card"})
        except (RequestError, HTTPStatusError) as e:
            logger.error(f"Page {page} failed after {MAX_RETRIES + 1} attempts: {e}")
            # Return the exception object so the caller can handle it without aborting the whole gather
            return e
        except Exception as e:
            logger.exception(f"Unexpected error fetching page {page}: {e}")
            return e

    def _process_page_cards(self, listing_cards: list) -> int:
        """Process listing cards from a page and return count of new listings"""
        page_count = 0
        for card in listing_cards:
            listing = self._extract_listing_card(card)

            if listing and listing["link"] not in self.seen_links:
                self.seen_links.add(listing["link"])
                self.listings.append(listing)
                page_count += 1

        return page_count

    async def _price_slices(self, url: str, lo: int, hi: int) -> list[tuple[int, int, int]]:
        """Split [lo, hi] until each slice has < OLX_RESULT_CAP results; returns (lo, hi, pages)."""
        if not self.client:
            raise RuntimeError("Client not initialized - use 'async with' context manager")
        response = await self.client.get(url, params=self._build_search_params(lo, hi, 1))
        totals = parse_listing_totals(response.text)
        if totals is None:
            logger.warning(f"Could not read result count for {lo:,}-{hi:,}; not splitting")
            return [(lo, hi, 0)]
        total, pages = totals
        if total < OLX_RESULT_CAP or hi - lo <= MIN_PRICE_SLICE_KZT:
            logger.info(f"💰 {lo:,}-{hi:,} KZT: {total} listings, {pages} pages")
            return [(lo, hi, pages)]
        mid = (lo + hi) // 2
        logger.info(
            f"✂️  {lo:,}-{hi:,} KZT hits OLX's {OLX_RESULT_CAP}-result cap, splitting at {mid:,}"
        )
        return await self._price_slices(url, lo, mid) + await self._price_slices(url, mid + 1, hi)

    async def scrape_listing_cards(
        self, min_price=None, max_price=None, max_pages=None, days_back=None
    ):
        """
        Scrape listing cards with CONCURRENT page fetching (10-30x faster!)
        Uses config.py settings by default, but can be overridden
        """
        params = self._setup_scrape_params(min_price, max_price, max_pages, days_back)
        self._log_scrape_start(params)

        url = config.get_search_url()
        max_pages_val = params["max_pages"]
        tasks = []

        slices = await self._price_slices(url, params["min_price"], params["max_price"])
        for lo, hi, pages in slices:
            # max_pages caps each price slice; 0 pages means the count was unreadable
            slice_pages = min(pages, max_pages_val) if pages else max_pages_val
            for page in range(1, slice_pages + 1):
                search_params = self._build_search_params(lo, hi, page)
                tasks.append(self._fetch_page_listings(url, search_params, page, slice_pages))

        total_tasks = len(tasks)
        logger.info(f"⚡ Executing {total_tasks} concurrent page fetches...")
        start_time = time.time()

        results = []
        # Use tqdm_asyncio.gather with total= so progress bar displays properly

        try:
            results = await tqdm_asyncio.gather(
                *tasks,
                total=total_tasks,
                desc="📄 Fetching pages (concurrent)",
                unit="page",
                colour="cyan",
                leave=False,
                position=0,
                dynamic_ncols=True,
            )

            elapsed = time.time() - start_time
            logger.info(
                f"✅ All pages fetched in {elapsed:.2f}s (avg: {elapsed / total_tasks:.2f}s/page)"
            )

        except Exception as e:
            logger.error(f"Unexpected error during concurrent fetch: {e}", exc_info=True)
            # At this point you may decide to continue with partial results or abort
            # e.g. `results = []`

        # Process results
        successful = 0
        failed = 0
        for page_idx, result in enumerate(results, start=1):
            if isinstance(result, Exception):
                logger.error(f"❌ Page {page_idx} failed: {result}")
                failed += 1
                continue
            if not result:
                logger.warning(f"No listings found on page {page_idx}")
                continue
            page_count = self._process_page_cards(result)
            successful += 1
            logger.info(
                f"✅ Page {page_idx}: +{page_count} new listings (Total: {len(self.listings)})"
            )

        logger.info("--- ASYNC SCRAPING COMPLETE ---")
        logger.info(
            f"✅ Total collected: {len(self.listings)} unique listings (successful pages: {successful}, failed: {failed})"
        )

        return self.listings

    def _extract_card_link(self, card) -> str | None:
        """Extract link from listing card"""
        link_elem = card.find("a", href=True)
        if not link_elem:
            return None
        return urljoin(self.base_url, link_elem["href"])

    def _extract_card_title(self, card) -> str:
        """Extract title from listing card"""
        # Try h6 first, then h4
        title_elem = card.find("h6") or card.find("h4")
        return title_elem.text.strip() if title_elem else "Unknown"

    def _extract_card_price(self, card) -> int:
        """Extract price from listing card"""
        price_elem = card.find("p", {"data-testid": "ad-price"})
        if price_elem:
            price_text = price_elem.text.strip()
            return self._extract_price(price_text)
        return 0

    def _extract_card_location(self, card) -> str:
        """Extract location from listing card"""
        location_elem = card.find("p", {"data-testid": "location-date"})
        return location_elem.text.strip() if location_elem else "N/A"

    def _detect_card_status(self, title: str) -> str:
        """Detect if phone is new or used from title"""
        title_lower = title.lower()
        new_keywords = ["новый", "новое", "новая"]
        return "Новый" if any(keyword in title_lower for keyword in new_keywords) else "Б/у"

    def _extract_card_image(self, card) -> str:
        """Extract image URL from listing card"""
        img_elem = card.find("img")
        return img_elem.get("src", "") if img_elem else ""

    def _extract_listing_card(self, card):
        """Extract data from listing card"""
        try:
            # Extract link (required field)
            link = self._extract_card_link(card)
            if not link:
                return None

            # Extract other fields
            title = self._extract_card_title(card)
            price = self._extract_card_price(card)
            location = self._extract_card_location(card)
            status = self._detect_card_status(title)
            image_url = self._extract_card_image(card)

            # Detect brand
            brand, phone_type, confidence = self.detect_phone_brand(title)

            return {
                "title": title,
                "price": price,
                "status": status,
                "location": location,
                "link": link,
                "image_url": image_url,
                "detected_brand": brand,
                "phone_type": phone_type,
                "brand_confidence": confidence,
                "scraped_at": datetime.now().isoformat(),
                **self.ad_meta.get(ad_id(link) or "", {}),
            }

        except Exception as e:
            logger.warning(f"Error parsing card: {e}")
            return None

    def _extract_price(self, price_text):
        """Extract numeric price"""
        price_text = (
            price_text.replace(" ", "").replace("\xa0", "").replace("тг", "").replace(".", "")
        )
        match = re.search(r"(\d+)", price_text)
        return int(match.group(1)) if match else 0

    def merge_with_existing(self, existing_file=None, use_session_dir=True):
        """Merge with existing data from same session only"""
        if use_session_dir:
            # Get session-specific file
            output_files = config.get_output_files()
            existing_file_path = output_files["all_listings"]
        else:
            if existing_file is None:
                existing_file = config.ALL_LISTINGS_FILE
            existing_file_path = Path(existing_file)

        try:
            with existing_file_path.open(encoding="utf-8") as f:
                existing_data = json.load(f)
                existing_listings = existing_data.get("listings", [])

            logger.info(f"📂 Loading existing session data: {len(existing_listings)} listings")

            # Get existing links
            existing_links = {item["link"] for item in existing_listings if "link" in item}

            # Add new listings that don't exist
            new_count = 0
            for listing in self.listings:
                if listing["link"] not in existing_links:
                    existing_listings.append(listing)
                    existing_links.add(listing["link"])
                    new_count += 1

            logger.info(f"✅ Added {new_count} new listings")
            logger.info(f"📊 Total after merge: {len(existing_listings)} listings")

            return existing_listings

        except FileNotFoundError:
            logger.info("📝 No existing session data found, starting fresh")
            return self.listings

    def _get_output_files(self, use_session_dir: bool) -> tuple[dict, str]:
        """Get output file paths based on configuration"""
        if use_session_dir:
            output_files = config.get_output_files()
            results_dir = config.get_results_dir()
            logger.info(f"📁 Session: {config.get_session_name()}")
        else:
            output_files = {
                "all_listings": config.ALL_LISTINGS_FILE,
                "iphones": config.IPHONES_FILE,
                "androids": config.ANDROIDS_FILE,
                "unknown": config.UNKNOWN_FILE,
            }
            results_dir = config.RESULTS_DIR
        return output_files, results_dir

    def categorize_listings(self, all_listings: list) -> tuple[list, list, list]:
        """Categorize listings by phone type"""
        iphones = [listing for listing in all_listings if listing.get("phone_type") == "iphone"]
        androids = [listing for listing in all_listings if listing.get("phone_type") == "android"]
        unknown = [listing for listing in all_listings if listing.get("phone_type") == "unknown"]

        logger.info("CATEGORIZATION:")
        logger.info(f"  iPhones: {len(iphones)}")
        logger.info(f"  Android: {len(androids)}")
        logger.info(f"  Unknown: {len(unknown)}")
        logger.info(f"  Total: {len(all_listings)}")
        return iphones, androids, unknown

    def _apply_phone_filter(self, iphones: list, androids: list) -> tuple[list, list]:
        """Apply phone type filter if specified"""
        if config.PHONE_TYPE_FILTER != "both":
            logger.info(f"Applying phone type filter: {config.PHONE_TYPE_FILTER}")
            if config.PHONE_TYPE_FILTER == "iphone":
                return iphones, []
            if config.PHONE_TYPE_FILTER == "android":
                return [], androids
        return iphones, androids

    def _save_all_listings(self, all_listings: list, output_file: str) -> None:
        """Save complete listings file"""
        write_json_atomic(
            output_file,
            {
                "total": len(all_listings),
                "scraped_at": datetime.now().isoformat(),
                "configuration": config.get_config_summary(),
                "scraper_mode": "async_concurrent",
                "listings": all_listings,
            },
        )
        logger.info(f"✅ Saved all listings to: {config.display_path(output_file)}")

    def _save_categories(
        self, iphones: list, androids: list, unknown: list, output_files: dict, results_dir: str
    ) -> None:
        """Save categorized phone lists"""
        write_json_atomic(output_files["iphones"], {"count": len(iphones), "phones": iphones})

        write_json_atomic(output_files["androids"], {"count": len(androids), "phones": androids})

        write_json_atomic(output_files["unknown"], {"count": len(unknown), "phones": unknown})

        logger.info(f"✅ Saved categories to: {config.display_path(results_dir)}")

    def _log_unknown_samples(self, unknown: list) -> None:
        """Log sample of unknown listings"""
        if unknown:
            logger.info(f"--- STILL UNKNOWN ({len(unknown)}) ---")
            for i, item in enumerate(unknown[:10], 1):
                logger.info(f"  {i}. {item['title'][:70]} - {item['price']:,} KZT")

    def save_results(self, all_listings, use_session_dir=True):
        """Save categorized results"""
        logger.info("=" * 80)
        logger.info("SAVING RESULTS")
        logger.info("=" * 80)

        # Get output configuration
        output_files, results_dir = self._get_output_files(use_session_dir)

        # Categorize listings
        iphones, androids, unknown = self.categorize_listings(all_listings)

        # Apply filters
        iphones, androids = self._apply_phone_filter(iphones, androids)

        # Save all listings
        self._save_all_listings(all_listings, output_files["all_listings"])

        # Save by category
        self._save_categories(iphones, androids, unknown, output_files, results_dir)

        # Save session info if using session directories
        if use_session_dir:
            session_info_file = config.save_session_info()
            logger.info(f"✅ Saved session info to: {config.display_path(session_info_file)}")

        # Show unknown samples
        self._log_unknown_samples(unknown)

        return iphones, androids, unknown


async def main():
    """Async main function"""
    logger.info("🚀 ASYNC OLX SCRAPER Concurrent page fetching - 10-30x faster!")

    # Show current configuration
    # config.print_config()

    # Validate configuration
    if not config.validate_config():
        logger.error("❌ Configuration validation failed! Please fix config.py")
        return

    # Use async context manager
    async with AsyncOLXScraper() as scraper:
        # Scrape with config settings (can be overridden with command args)
        new_listings = await scraper.scrape_listing_cards()

        if not new_listings:
            logger.error("❌ No new listings found!")
            return

        # Merge with existing (only from same session)
        all_listings = scraper.merge_with_existing(use_session_dir=True)

        # Save results
        iphones, androids, unknown = scraper.save_results(all_listings, use_session_dir=True)

        # Statistics
        logger.info("=" * 80)
        logger.info("FINAL STATISTICS")
        logger.info("=" * 80)

        total = len(all_listings)
        logger.info(f"Total listings: {total}")
        logger.info(f"iPhones: {len(iphones)} ({len(iphones) / total * 100:.1f}%)")
        logger.info(f"Android: {len(androids)} ({len(androids) / total * 100:.1f}%)")
        logger.info(f"Unknown: {len(unknown)} ({len(unknown) / total * 100:.1f}%)")

        # Brand breakdown
        brands = {}
        for listing in androids:
            brand = listing.get("detected_brand", "unknown")
            brands[brand] = brands.get(brand, 0) + 1

        logger.info("--- TOP ANDROID BRANDS ---")
        for brand, count in sorted(brands.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  • {brand:15s}: {count:3d} phones")

        logger.info("✅ Async scraping completed successfully!")

#!/usr/bin/env python3
"""
Advanced Android Phone Analyzer with Specifications
- Score and rank all Android phones
- Fetch specifications from APIs
- Compare with market prices
- Generate detailed recommendations
- Comprehensive logging
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# Import utilities - moved to top-level
from src.ai.cloud_llm import CloudLLMAnalyzer
from src.ai.gemini import GeminiAnalyzer

# Import market prices and scoring configuration
from src.analysis.market_data import MARKET_PRICES
from src.analysis.phone_normalizer import PhoneNormalizer
from src.analysis.scoring import (
    get_age_score,
    get_battery_health_score,  # 🆕 NEW Phase 1
    get_brand_score,
    get_camera_score,
    get_condition_score,
    get_discount_score,
    get_display_score,  # 🆕 NEW Phase 2
    get_dxomark_score,
    get_price_range_score,
    get_processor_score,  # 🆕 NEW Phase 1
    get_ram_score,
    get_storage_score,
    get_tier_score,
    get_warranty_score,  # 🆕 NEW Phase 2
)

# Import config from src.core
from src.core import config, constants

# Import constants
from src.core.constants import MAX_DESCRIPTION_DISPLAY_LENGTH, MAX_FAILED_PHONES_DISPLAY
from src.detection.patterns import strip_exchange_wish
from src.enrichment.spec_enrichment import SpecEnricher
from src.fetchers.listing_fetcher import ListingDetailFetcher
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


# Words that make a model a different (usually cheaper) variant than the base number
VARIANT_SUFFIX = (
    r"\s*(?:t\b|s\b|lite|лайт|pro|про|plus|плюс|\+|ultra|ультра|fe\b|max|макс|mini|мини|neo|нео)"
)
XIAOMI_SUFFIX_KEYS = {"t": "t", "lite": " lite", "лайт": " lite", "pro": " pro", "про": " pro"}


def listing_warnings(phone: dict[str, Any]) -> list[str]:
    """Seller/location caveats shown next to a listing (they don't change its score)."""
    warnings = []
    if phone.get("is_business"):
        warnings.append(
            "🏪 SHOP, not a private seller: ask about warranty, check it's not a refurb"
        )
    city = phone.get("city")
    if city and city != config.HOME_CITY:
        warnings.append(f"📍 OUTSIDE {config.HOME_CITY.upper()}: {city}, you'll need to travel")
    return warnings


def max_plausible_discount(release_year: int, now_year: int | None = None) -> int:
    """Largest believable discount (%) off launch price for a used phone of this age."""
    age = max(0, (now_year or datetime.now().year) - release_year)
    return min(
        constants.PLAUSIBLE_DISCOUNT_BASE + constants.PLAUSIBLE_DISCOUNT_PER_YEAR * age,
        constants.PLAUSIBLE_DISCOUNT_CAP,
    )


# TODO: Install these libraries for better spec lookup:
# uv add phonespecs-api (if available)
# uv add whisk (github.com/epuerta9/whisk)
# For now, we'll use fallback methods


class AndroidAnalyzer:
    """Analyzer for Android phone listings with AI-powered insights"""

    def __init__(  # noqa: PLR0913
        self,
        use_gemini: bool = False,
        gemini_use_photos: bool = False,
        gemini_top_n: int | None = None,
        reset_gemini_cache: bool = False,
        gemini_async: bool = False,
        use_cerebras: bool = False,
        cerebras_model: str = "default",
        use_openrouter: bool = False,
        openrouter_model: str = "default",
        use_vercel: bool = False,
        vercel_model: str = "default",
        enrich_with_kimovil: bool = True,  # 🆕 NEW Phase 3
    ) -> None:
        logger.info("Initializing Android Analyzer")

        # Load market prices from external configuration
        self.market_prices = MARKET_PRICES
        self.gemini_top_n = gemini_top_n

        # 🆕 NEW Phase 3: Initialize spec enricher
        self.spec_enricher = None
        if enrich_with_kimovil:
            try:
                self.spec_enricher = SpecEnricher()
                logger.info("✅ Kimovil spec enrichment enabled (95-99% success rate)")
            except Exception as e:
                logger.warning(f"⚠️  Failed to initialize spec enricher: {e}")
                logger.warning("   Continuing without Kimovil enrichment")
        else:
            logger.info("ℹ️  Kimovil spec enrichment disabled")

        # Initialize AI analyzers
        self.gemini = self._init_gemini_analyzer(
            use_gemini, gemini_use_photos, gemini_top_n, reset_gemini_cache, gemini_async
        )
        self.cloud_llm = self._init_cloud_llm_analyzer(
            use_cerebras, cerebras_model, use_openrouter, openrouter_model, use_vercel, vercel_model
        )

        logger.info(f"Loaded market price data for {len(self.market_prices)} phone models")

    def _init_gemini_analyzer(
        self,
        use_gemini: bool,
        use_photos: bool,
        top_n: int | None,
        reset_cache: bool,
        use_async: bool,
    ) -> GeminiAnalyzer | None:
        """Initialize Gemini AI analyzer"""
        if not use_gemini:
            return None

        logger.info("Initializing Gemini AI analyzer...")
        gemini = GeminiAnalyzer(use_photos=use_photos, use_async=use_async)

        if reset_cache and gemini.enabled:
            logger.info("🗑️  Clearing Gemini cache...")
            gemini.clear_cache()

        if gemini.enabled:
            logger.info("✅ Gemini AI analyzer ready")
            logger.info(f"📸 Photo analysis {'ENABLED' if use_photos else 'DISABLED'}")
            logger.info(f"⚡ {'Async' if use_async else 'Sync'} mode")
            count = top_n if top_n else config.TOP_RECOMMENDATIONS_COUNT
            logger.info(f"🎯 Will analyze top {count} recommendations")
        else:
            logger.warning("⚠️  Gemini AI analyzer not available")

        return gemini

    def _init_cloud_llm_analyzer(  # noqa: PLR0913
        self,
        use_cerebras: bool,
        cerebras_model: str,
        use_openrouter: bool,
        openrouter_model: str,
        use_vercel: bool,
        vercel_model: str,
    ) -> CloudLLMAnalyzer | None:
        """Initialize Free Cloud LLM analyzer (Cerebras/OpenRouter/Vercel)"""
        if not (use_cerebras or use_openrouter or use_vercel):
            return None

        logger.info("Initializing Free Cloud LLM analyzer...")

        # Priority: Cerebras > OpenRouter > Vercel (fastest to slowest)
        if use_cerebras:
            cloud_llm = CloudLLMAnalyzer(provider="cerebras", model=cerebras_model)
        elif use_openrouter:
            cloud_llm = CloudLLMAnalyzer(provider="openrouter", model=openrouter_model)
        else:  # use_vercel
            cloud_llm = CloudLLMAnalyzer(provider="vercel", model=vercel_model)

        if cloud_llm and cloud_llm.enabled:
            logger.info(f"✅ {cloud_llm.config['name']} ready (Tier 2 fallback)")
            logger.info(f"   Model: {cloud_llm.model}")
            logger.info(f"   Speed: {cloud_llm.config['speed']}")
            return cloud_llm

        logger.warning("⚠️  Free Cloud LLM not available")
        return None

    def extract_model_from_title(self, title):
        """
        Extract specific model from title for market price lookup

        🆕 ENHANCED: Now supports Cyrillic, spaces, and all major variants
        """
        title_lower = title.lower()

        # Pattern matching for models (order matters - most specific first!)
        patterns = [
            # Samsung Z Fold/Flip series
            (r"z\s*(?:фолд|fold)\s*(\d+)", lambda m: f"samsung z fold{m.group(1)}"),
            (r"z\s*(?:флип|flip)\s*(\d+)", lambda m: f"samsung z flip{m.group(1)}"),
            # Samsung S series (supports Cyrillic 'с' and spaces)
            (r"\b[sс]\s*(\d+)\s*fe", lambda m: f"samsung s{m.group(1)} fe"),
            (r"\b[sс]\s*(\d+)\s*(?:ultra|ультра)", lambda m: f"samsung s{m.group(1)} ultra"),
            (r"\b[sс]\s*(\d+)\s*(?:plus|\+|плюс)", lambda m: f"samsung s{m.group(1)} plus"),
            (r"galaxy\s*s\s*(\d+)\s*fe", lambda m: f"samsung s{m.group(1)} fe"),
            (r"galaxy\s*s\s*(\d+)\s*(?:ultra|ультра)", lambda m: f"samsung s{m.group(1)} ultra"),
            (r"galaxy\s*s\s*(\d+)\s*(?:plus|\+|плюс)", lambda m: f"samsung s{m.group(1)} plus"),
            (r"\b[sс]\s*(\d+)", lambda m: f"samsung s{m.group(1)}"),
            (r"galaxy\s*s\s*(\d+)", lambda m: f"samsung s{m.group(1)}"),
            # Samsung A series (Cyrillic support)
            (r"[aа]\s*(\d+)", lambda m: f"samsung a{m.group(1)}"),
            # Xiaomi (Cyrillic + typos: сяоми, ксяоми, xioami, xiomi)
            (
                r"(?:xiaomi|сяоми|ксяоми|шаоми|xioami|xiomi)\s*(\d+)s?\s*(?:ultra|ультра)",
                lambda m: f"xiaomi {m.group(1)}{'s' if 's' in m.group(0) else ''} ultra",
            ),
            (
                r"(?:xiaomi|сяоми|ксяоми|шаоми|xioami|xiomi)\s*(\d+)\s*t\s*pro",
                lambda m: f"xiaomi {m.group(1)}t pro",
            ),
            (
                r"(?:xiaomi|сяоми|ксяоми|шаоми|xioami|xiomi)\s*(\d+)\s*(t|lite|лайт|pro|про)?\b",
                lambda m: f"xiaomi {m.group(1)}" + XIAOMI_SUFFIX_KEYS.get(m.group(2) or "", ""),
            ),
            (r"\bmi\s+(\d+)\s*(?:ultra|ультра)", lambda m: f"xiaomi {m.group(1)} ultra"),
            (r"\bmi\s+(\d+)", lambda m: f"xiaomi {m.group(1)}"),
            # Redmi Note (Cyrillic: редми, ноте, нот, про)
            (
                r"(?:redmi|редми|ридми|redmy)\s*(?:note|ноте?|нод)\s*(\d+)\s*(?:pro|про)",
                lambda m: f"redmi note {m.group(1)} pro",
            ),
            (
                r"(?:redmi|редми|ридми|redmy)\s*(?:note|ноте?|нод)\s*(\d+)",
                lambda m: f"redmi note {m.group(1)}",
            ),
            # Standalone "Note X pro" - assume Redmi
            (
                r"\b(?:note|нот|ноте)\s*(\d+)\s*(?:pro|про)",
                lambda m: f"redmi note {m.group(1)} pro",
            ),
            (r"\b(?:note|нот|ноте)\s*(\d+)", lambda m: f"redmi note {m.group(1)}"),
            # Redmi base models
            (r"(?:redmi|редми|ридми)\s*(\d+)x?", lambda m: f"redmi {m.group(1)}"),
            # POCO (supports spaces: "poco f 6 pro")
            (r"poco\s*f\s*(\d+)\s*pro", lambda m: f"poco f{m.group(1)} pro"),
            (r"poco\s*f\s*(\d+)", lambda m: f"poco f{m.group(1)}"),
            (r"poco\s*x\s*(\d+)\s*pro", lambda m: f"poco x{m.group(1)} pro"),
            (r"poco\s*x\s*(\d+)", lambda m: f"poco x{m.group(1)}"),
            (r"poco\s*m\s*(\d+)", lambda m: f"poco m{m.group(1)}"),
            # Google Pixel
            (r"pixel\s*(\d+)\s*(?:pro|про)", lambda m: f"pixel {m.group(1)} pro"),
            (r"pixel\s*(\d+)\s*a", lambda m: f"pixel {m.group(1)}a"),
            (r"pixel\s*(\d+)", lambda m: f"pixel {m.group(1)}"),
            # OnePlus (supports "One plus", "Oneplus", "One Plus")
            (r"(?:oneplus|one\s*plus)\s*(\d+)\s*r", lambda m: f"oneplus {m.group(1)}r"),
            (r"(?:oneplus|one\s*plus)\s*nord\s*(\d+)", lambda m: f"oneplus nord {m.group(1)}"),
            (r"(?:oneplus|one\s*plus)\s*nord", lambda m: "oneplus nord"),
            (
                r"(?:oneplus|one\s*plus)\s*(\d+)t?",
                lambda m: f"oneplus {m.group(1)}{'t' if 't' in m.group(0) else ''}",
            ),
            # Huawei
            (r"(?:huawei|хуавей)\s*p\s*(\d+)\s*(?:pro|про)", lambda m: f"huawei p{m.group(1)} pro"),
            (r"(?:huawei|хуавей)\s*p\s*(\d+)", lambda m: f"huawei p{m.group(1)}"),
            (
                r"(?:huawei|хуавей)?\s*mate\s*(\d+)\s*(?:pro|про)",
                lambda m: f"huawei mate {m.group(1)} pro",
            ),
            (r"(?:huawei|хуавей)?\s*mate\s*(\d+)", lambda m: f"huawei mate {m.group(1)}"),
            # iPhone (Cyrillic: айфон, про, макс)
            (
                r"(?:iphone|айфон|aйфон|aifon|ayfon)\s*xs\s*(?:max|макс|мах)",
                lambda m: "iphone xs max",
            ),
            (
                r"(?:iphone|айфон|aйфон|aifon|ayfon)\s*(\d+|xs|xr|x|se)\s*(?:pro|про)\s*(?:max|макс|мах)",
                lambda m: f"iphone {m.group(1)} pro max",
            ),
            (
                r"(?:iphone|айфон|aйфон|aifon|ayfon)\s*(\d+|xs|xr|x|se)\s*(?:pro|про)",
                lambda m: f"iphone {m.group(1)} pro",
            ),
            (
                r"(?:iphone|айфон|aйфон|aifon|ayfon)\s*(\d+)\s*(?:plus|\+|плюс)",
                lambda m: f"iphone {m.group(1)} plus",
            ),
            (
                r"(?:iphone|айфон|aйфон|aifon|ayfon)\s*(\d+|xs|xr|x|se)",
                lambda m: f"iphone {m.group(1)}",
            ),
        ]

        for pattern, formatter in patterns:
            match = re.search(pattern, title_lower)
            if match:
                model = formatter(match)
                logger.debug(f"Extracted model '{model}' from title")
                return model

        return None

    def get_market_price_info(self, title):
        """Get market price information for a phone"""
        model = self.extract_model_from_title(title)

        # Extractor says "samsung s20 plus"; the price table keys it "samsung s20+"
        for key in (model, model and model.replace(" plus", "+")):
            if key and key in self.market_prices:
                logger.debug(f"Found market price for {key}")
                return self.market_prices[key]

        # Fallback: try partial matching
        title_lower = title.lower()
        for model_key, info in self.market_prices.items():
            # "xiaomi 13" must not match "xiaomi 13 lite": a variant has its own (lower) price
            if re.search(rf"\b{re.escape(model_key)}(?!\w|{VARIANT_SUFFIX})", title_lower):
                logger.debug(f"Partial match for {model_key}")
                return info

        logger.debug(f"No market price found for: {title[:50]}")
        return None

    def calculate_value_score(self, phone: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0912, PLR0915
        """Calculate comprehensive value score

        🆕 NEW Phase 3: Now uses Kimovil specs for MUCH MORE ACCURATE scoring!
        🆕 NEW Phase 4: Adds normalized phone names for better readability!

        Args:
            phone: Phone data dictionary (may include kimovil_specs)

        Returns:
            Updated phone dictionary with value_score, value_factors, and normalized_title
        """
        score = 0
        factors = []

        # Score the phone being sold, not the one wanted in exchange
        sold_title = strip_exchange_wish(phone["title"])
        title = sold_title.lower()
        price = phone["price"]
        specs = phone.get("kimovil_specs")  # 🆕 Get Kimovil specs if available

        # 🆕 NEW Phase 4: Add normalized title for better readability
        # Format: "Brand Model (original title)"
        # Example: "Samsung S25 Ultra (Самсунг с 25 ультра s 25 ultra)"
        detected_brand = phone.get("detected_brand")
        phone["normalized_title"] = PhoneNormalizer.normalize_phone_name(sold_title, detected_brand)

        # Get market info
        market_info = self.get_market_price_info(title)

        if market_info:
            initial_price = market_info["initial"]
            year = market_info["year"]
            tier = market_info["tier"]

            # Calculate discount percentage
            discount = ((initial_price - price) / initial_price) * 100

            # Apply discount scoring from config
            discount_points, discount_label = get_discount_score(discount)
            if discount_label:
                score += discount_points
                factors.append(discount_label)

            phone["market_initial_price"] = initial_price
            phone["discount_percent"] = discount

            max_plausible = max_plausible_discount(year)
            if discount > max_plausible:
                score -= constants.SUSPICIOUS_DISCOUNT_PENALTY
                factors.append(
                    f"🚩 {discount:.0f}% off a {year} model (max plausible {max_plausible}%): "
                    "likely copy, scam or broken"
                )
            phone["release_year"] = year

            # Apply age scoring from config
            age_points, age_label = get_age_score(year)
            if age_label:
                score += age_points
                factors.append(age_label)

            # Apply tier scoring from config
            tier_points = get_tier_score(tier)
            score += tier_points
            # Add tier label (be specific about flagship vs mid-flagship)
            if tier == "flagship-ultra":
                factors.append("⭐⭐⭐ Ultra Flagship")
            elif tier == "flagship+":
                factors.append("⭐⭐ Flagship Plus")
            elif tier == "flagship":
                factors.append("⭐ Flagship quality")
            elif tier == "flagship-lite":
                factors.append("⭐ Flagship Lite (FE)")
            elif tier == "mid-flagship":
                factors.append("🔶 Mid-Flagship (not true flagship)")

        else:
            # No market data - use brand heuristics from config
            phone["market_initial_price"] = None
            phone["discount_percent"] = None
            phone["release_year"] = None

            brand = phone.get("detected_brand", "unknown")
            brand_points = get_brand_score(brand)
            score += brand_points

        # Apply storage scoring from config (🆕 now uses specs if available)
        storage_points, storage_label = get_storage_score(title, specs)
        if storage_label:
            score += storage_points
            factors.append(storage_label)

        # Apply RAM scoring from config (🆕 now uses specs if available)
        ram_points, ram_label = get_ram_score(title, specs)
        if ram_label:
            score += ram_points
            factors.append(ram_label)

        # Apply price range scoring from config
        price_points, price_label = get_price_range_score(price)
        if price_label:
            score += price_points
            factors.append(price_label)

        # Apply condition scoring from config
        # Title too: "на запчасти" often appears only there, and descriptions are fetched for top N only
        description = f"{phone['title']}\n{phone.get('description') or ''}"
        condition_points, condition_factors = get_condition_score(description)
        score += condition_points
        factors.extend(condition_factors)

        # Apply camera scoring from config
        model = self.extract_model_from_title(title)
        camera_points, camera_label = get_camera_score(model, tier if market_info else None)
        if camera_label:
            score += camera_points
            factors.append(camera_label)
            phone["camera_score"] = camera_points
            phone["dxomark_score"] = get_dxomark_score(model)
        else:
            phone["camera_score"] = None
            phone["dxomark_score"] = None

        # 🆕 NEW: Apply processor scoring (now uses specs if available)
        processor_points, processor_label = get_processor_score(
            phone["title"],
            tier if market_info else None,
            specs,  # 🆕 Pass Kimovil specs
        )
        if processor_label:
            score += processor_points
            factors.append(processor_label)
            phone["processor_score"] = processor_points
        else:
            phone["processor_score"] = None

        # 🆕 NEW: Apply battery health scoring (now uses specs if available)
        battery_points, battery_label = get_battery_health_score(
            description, specs, title=sold_title
        )
        if battery_label:
            score += battery_points
            factors.append(battery_label)
            phone["battery_health_score"] = battery_points
        else:
            phone["battery_health_score"] = None

        # 🆕 NEW Phase 2: Apply display quality scoring (now uses specs if available)
        display_points, display_labels = get_display_score(phone["title"], description, specs)
        if display_labels:
            score += display_points
            factors.extend(display_labels)
            phone["display_score"] = display_points
        else:
            phone["display_score"] = None

        # 🆕 NEW Phase 2: Apply warranty/seller scoring
        warranty_points, warranty_labels = get_warranty_score(phone["title"], description)
        if warranty_labels:
            score += warranty_points
            factors.extend(warranty_labels)
            phone["warranty_score"] = warranty_points
        else:
            phone["warranty_score"] = None

        phone["value_score"] = max(score, 0)
        phone["warnings"] = listing_warnings(phone)
        phone["value_factors"] = phone["warnings"] + factors

        return phone

    def _load_androids_from_session(self) -> list[dict[str, Any]]:
        """Load Android phones from session-based directory structure.

        Returns:
            List of Android phone dictionaries

        Raises:
            FileNotFoundError: If no session files are found
        """
        output_files = config.get_output_files()
        analyzed_file = output_files["analyzed_androids"]
        androids_file = output_files["androids"]

        # Fresh categorized files are the source of truth; iPhones join when the
        # session's phone type asks for them
        raw_files = {"android": [androids_file], "iphone": [output_files["iphones"]]}.get(
            config.PHONE_TYPE_FILTER, [androids_file, output_files["iphones"]]
        )
        raw_files = [f for f in raw_files if f.exists()]
        if not raw_files:
            logger.warning("No session files found, checking legacy location")
            return self._load_androids_from_legacy()

        phones = []
        for raw_file in raw_files:
            logger.info(f"📝 Loading from raw file: {raw_file.name}")
            with Path(raw_file).open(encoding="utf-8") as f:
                phones.extend(json.load(f)["phones"])

        cached = self._load_cached_details(analyzed_file)
        # Fresh fields (price, title) win; cached ones (description, photos, specs) fill the rest
        phones = [{**cached[p["link"]], **p} if p.get("link") in cached else p for p in phones]
        logger.info(
            f"✅ Loaded {len(phones)} phones ({sum(p.get('link') in cached for p in phones)} "
            "with cached descriptions)"
        )
        return phones

    @staticmethod
    def _load_cached_details(analyzed_file: Path) -> dict[str, dict[str, Any]]:
        """Previously fetched listing details from the last analysis, keyed by link."""
        if not analyzed_file.exists():
            return {}
        try:
            with Path(analyzed_file).open(encoding="utf-8") as f:
                previous = json.load(f)["phones"]
        except (OSError, ValueError, KeyError) as e:
            logger.warning(f"Ignoring unreadable analyzed file {analyzed_file.name}: {e}")
            return {}
        return {p["link"]: p for p in previous if p.get("details_fetched") and p.get("link")}

    def _load_androids_from_legacy(self) -> list[dict[str, Any]]:
        """Load Android phones from legacy file location.

        Returns:
            List of Android phone dictionaries

        Raises:
            FileNotFoundError: If legacy file not found
        """
        androids_file = config.ANDROIDS_FILE
        try:
            with Path(androids_file).open(encoding="utf-8") as f:
                data = json.load(f)
                return data["phones"]
        except FileNotFoundError:
            logger.error(f"File not found: {androids_file}")
            logger.error(f"❌ Please run the scraper first to generate {androids_file}")
            raise

    def _calculate_all_scores(self, androids: list[dict[str, Any]]) -> None:
        """Calculate value scores for all Android phones in-place.

        Args:
            androids: List of Android phone dictionaries (modified in-place)
        """
        logger.info("--- CALCULATING VALUE SCORES ---")

        # Use tqdm for progress visualization (mininterval=0 to always show updates)
        with logging_redirect_tqdm():
            for phone in tqdm(
                androids,
                desc="📊 Analyzing value scores",
                unit="phone",
                colour="yellow",
                mininterval=0,
                maxinterval=1,
                position=0,
                dynamic_ncols=True,
            ):
                self.calculate_value_score(phone)

        # Sort by value score
        androids.sort(key=lambda x: x.get("value_score", 0), reverse=True)
        logger.info(f"✅ Analysis complete! Analyzed {len(androids)} phones")

    def _fetch_top_phone_details(
        self, androids: list[dict[str, Any]], top_count: int
    ) -> list[dict[str, Any]]:
        """Fetch full details (description + photos) for top phones.

        Args:
            androids: List of Android phone dictionaries
            top_count: Number of top phones to fetch details for

        Returns:
            Updated list with fetched details
        """
        logger.info("--- FETCHING FULL DETAILS FOR TOP PHONES ---")
        logger.info("Fetching descriptions and photos for top recommendations...")

        async def _run_fetch():
            async with ListingDetailFetcher() as fetcher:
                return await fetcher.fetch_batch_details(androids, max_listings=top_count)

        logger.info(f"⚡ Launching async fetch for top {top_count} phones...")
        androids = asyncio.run(_run_fetch())

        with_description = sum(1 for p in androids[:top_count] if p.get("description"))
        logger.info(f"📝 Descriptions fetched: {with_description}/{top_count}")

        return androids

    def _log_gemini_estimation(self, gemini_count: int) -> None:
        """Log Gemini analysis start and time estimation"""
        logger.info(f"🤖 Phase 1: Running Gemini AI analysis on top {gemini_count} phones...")
        estimate_minutes = (gemini_count * 17) // 60
        logger.info(f"⏱️  Estimated time: ~{estimate_minutes}-{estimate_minutes + 2} minutes...")

    def _collect_gemini_failures(
        self, androids: list[dict[str, Any]], gemini_count: int
    ) -> list[int]:
        """Collect indices of phones that failed Gemini analysis"""
        return [
            i
            for i, phone in enumerate(androids[:gemini_count])
            if not phone.get("gemini_analysis", {}).get("analyzed")
        ]

    def _log_gemini_results(
        self, androids: list[dict[str, Any]], gemini_count: int, analyzed_count: int
    ) -> None:
        """Log Gemini analysis results"""
        failed_count = gemini_count - analyzed_count

        logger.info(f"✅ Gemini analyzed: {analyzed_count}/{gemini_count}")
        if failed_count > 0:
            logger.warning(
                f"⚠️  Gemini failures: {failed_count} (will use Tier 2 fallback if available)"
            )

        score_changes = sum(
            1 for p in androids[:gemini_count] if p.get("gemini_penalty") or p.get("gemini_bonus")
        )
        logger.info(f"📊 Scores adjusted by Gemini: {score_changes}")
        logger.info(f"✅ Gemini analysis complete! ({analyzed_count}/{gemini_count} successful)")

    def _run_gemini_analysis(
        self, androids: list[dict[str, Any]], gemini_count: int
    ) -> tuple[list[dict[str, Any]], list[int]]:
        """Run Gemini AI analysis on top phones.

        Args:
            androids: List of Android phone dictionaries
            gemini_count: Number of top phones to analyze with Gemini

        Returns:
            Tuple of (updated androids list, list of failed phone indices)
        """
        if not self.gemini or not self.gemini.enabled or gemini_count == 0:
            return androids, []

        # Log estimation and run analysis
        self._log_gemini_estimation(gemini_count)
        androids = self.gemini.analyze_batch(androids, max_phones=gemini_count)

        # Collect results
        analyzed_count = sum(
            1 for p in androids[:gemini_count] if p.get("gemini_analysis", {}).get("analyzed")
        )
        gemini_failures = self._collect_gemini_failures(androids, gemini_count)

        # Log results
        self._log_gemini_results(androids, gemini_count, analyzed_count)

        return androids, gemini_failures

    def _run_cloud_llm_fallback(
        self, androids: list[dict[str, Any]], gemini_failures: list[int]
    ) -> list[dict[str, Any]]:
        """Run Cloud LLM fallback analysis for Gemini failures.

        Args:
            androids: List of Android phone dictionaries
            gemini_failures: Indices of phones that failed Gemini analysis

        Returns:
            Updated list with fallback analysis
        """
        if not self.cloud_llm or not self.cloud_llm.enabled or not gemini_failures:
            return androids

        logger.info(
            f"--- 🔄 TIER 2 FALLBACK: {self.cloud_llm.config['name'].upper()} FOR GEMINI FAILURES ---"
        )
        logger.info(
            f"{self.cloud_llm.config['emoji']} Running {self.cloud_llm.config['name']} fallback "
            f"for {len(gemini_failures)} failed Gemini analyses..."
        )
        logger.info(
            f"   Failed phone indices: {gemini_failures[:MAX_FAILED_PHONES_DISPLAY]}"
            f"{'...' if len(gemini_failures) > MAX_FAILED_PHONES_DISPLAY else ''}"
        )

        # Analyze failed phones with Cloud LLM
        failed_phones = [androids[i] for i in gemini_failures]
        failed_phones = self.cloud_llm.analyze_batch(failed_phones, max_phones=len(failed_phones))

        # Put them back and identify new failures
        cloud_llm_failures = []
        for i, failed_phone in zip(gemini_failures, failed_phones, strict=False):
            androids[i] = failed_phone
            analysis_key = f"{self.cloud_llm.provider}_analysis"
            if not failed_phone.get(analysis_key, {}).get("analyzed"):
                cloud_llm_failures.append(i)

        # Log results
        tier2_success = len(gemini_failures) - len(cloud_llm_failures)
        logger.info(
            f"✅ {self.cloud_llm.config['name']} recovered: {tier2_success}/{len(gemini_failures)}"
        )
        if cloud_llm_failures:
            logger.warning(f"⚠️  {len(cloud_llm_failures)} analyses still failed")
        logger.info(
            f"✅ {self.cloud_llm.config['name']} Tier 2 complete! Recovered {tier2_success} analyses"
        )

        return androids

    def _run_cloud_llm_primary(
        self, androids: list[dict[str, Any]], analysis_count: int
    ) -> tuple[list[dict[str, Any]], list[int]]:
        """
        Run Cloud LLM AI analysis on top phones (PRIMARY provider)

        Args:
            androids: List of Android phone dictionaries
            analysis_count: Number of top phones to analyze

        Returns:
            Tuple of (updated androids list, list of failed phone indices)
        """
        if not self.cloud_llm or not self.cloud_llm.enabled or analysis_count == 0:
            return androids, []

        logger.info(f"--- 🚀 TIER 1 PRIMARY: {self.cloud_llm.config['name'].upper()} ANALYSIS ---")
        logger.info(
            f"{self.cloud_llm.config['emoji']} Analyzing top {analysis_count} phones with "
            f"{self.cloud_llm.config['name']} (ultra-fast, FREE)..."
        )
        logger.info("   Speed: ~0.1-0.2s per phone (100x faster than Gemini)")

        # Run analysis
        androids = self.cloud_llm.analyze_batch(androids, max_phones=analysis_count)

        # Collect results
        analysis_key = f"{self.cloud_llm.provider}_analysis"
        analyzed_count = sum(
            1 for p in androids[:analysis_count] if p.get(analysis_key, {}).get("analyzed")
        )
        cloud_failures = [
            i
            for i, phone in enumerate(androids[:analysis_count])
            if not phone.get(analysis_key, {}).get("analyzed")
        ]

        # Log results
        logger.info(
            f"✅ {self.cloud_llm.config['name']} analyzed: {analyzed_count}/{analysis_count}"
        )
        if cloud_failures:
            logger.warning(f"⚠️  {len(cloud_failures)} analyses failed (will retry with Gemini)")

        return androids, cloud_failures

    def _run_gemini_fallback(
        self, androids: list[dict[str, Any]], cloud_failures: list[int]
    ) -> list[dict[str, Any]]:
        """
        Run Gemini fallback analysis for Cloud LLM failures

        Args:
            androids: List of Android phone dictionaries
            cloud_failures: Indices of phones that failed Cloud LLM analysis

        Returns:
            Updated list with fallback analysis
        """
        if not self.gemini or not self.gemini.enabled or not cloud_failures:
            if cloud_failures and not (self.gemini and self.gemini.enabled):
                logger.warning(
                    f"⚠️  {len(cloud_failures)} Cloud LLM failures but Gemini fallback not enabled"
                )
            return androids

        logger.info("--- 🔄 TIER 2 FALLBACK: GEMINI FOR CLOUD LLM FAILURES ---")
        logger.info(f"🔮 Running Gemini fallback for {len(cloud_failures)} failed analyses...")
        logger.info(
            f"   Failed phone indices: {cloud_failures[:MAX_FAILED_PHONES_DISPLAY]}"
            f"{'...' if len(cloud_failures) > MAX_FAILED_PHONES_DISPLAY else ''}"
        )
        logger.info("   Note: Gemini is slower (~6.6s/phone) but higher quality")

        # Analyze failed phones with Gemini
        failed_phones = [androids[i] for i in cloud_failures]
        failed_phones = self.gemini.analyze_batch(failed_phones, max_phones=len(failed_phones))

        # Put them back and identify new failures
        gemini_failures = []
        for i, failed_phone in zip(cloud_failures, failed_phones, strict=False):
            androids[i] = failed_phone
            if not failed_phone.get("gemini_analysis", {}).get("analyzed"):
                gemini_failures.append(i)

        # Log results
        tier2_success = len(cloud_failures) - len(gemini_failures)
        logger.info(f"✅ Gemini recovered: {tier2_success}/{len(cloud_failures)}")
        if gemini_failures:
            logger.warning(f"❌ {len(gemini_failures)} analyses still failed (no more fallbacks)")
        logger.info(f"✅ Gemini Tier 2 complete! Recovered {tier2_success} analyses")

        return androids

    def _run_ai_analysis_pipeline(
        self, androids: list[dict[str, Any]], top_count: int
    ) -> list[dict[str, Any]]:
        """
        Run 2-tier AI analysis pipeline (Cloud LLM PRIMARY + Gemini fallback)

        Strategy (optimized for speed):
        1. Cloud LLM (Cerebras) as PRIMARY: 0.1-0.2s/phone, FREE, 2000-3000 tokens/sec
        2. Gemini as FALLBACK: 6.6s/phone, rate limited, only for Cloud LLM failures
        """
        logger.info("--- AI ANALYSIS OF TOP RECOMMENDATIONS (2-TIER OPTIMIZED) ---")

        # Determine analysis count
        analysis_count = self.gemini_top_n if self.gemini_top_n else top_count
        analysis_count = min(analysis_count, top_count)

        # Log strategy (Cloud LLM is now Tier 1!)
        logger.info("🤖 2-TIER AI ANALYSIS STRATEGY (OPTIMIZED):")
        if self.cloud_llm and self.cloud_llm.enabled:
            logger.info(
                f"   1️⃣  Tier 1 (Primary): {self.cloud_llm.config['name']} "
                f"(ultra-fast, FREE, 100x faster than Gemini)"
            )
        if self.gemini and self.gemini.enabled:
            logger.info("   2️⃣  Tier 2 (Fallback): Gemini (only for Cloud LLM failures)")

        if not (self.cloud_llm and self.cloud_llm.enabled) and not (
            self.gemini and self.gemini.enabled
        ):
            logger.warning("⚠️  No AI providers enabled!")
            return androids

        if self.cloud_llm and self.cloud_llm.enabled:
            # Phase 1: Cloud LLM analysis (PRIMARY - fast and free!)
            androids, cloud_failures = self._run_cloud_llm_primary(androids, analysis_count)

            # Phase 2: Gemini fallback (only for Cloud LLM failures)
            androids = self._run_gemini_fallback(androids, cloud_failures)
        else:
            # Gemini is the only provider: it runs as primary
            androids, _ = self._run_gemini_analysis(androids, analysis_count)

        # Re-sort after AI adjustments
        logger.info("🔄 Re-sorting by adjusted scores...")
        androids.sort(key=lambda x: x.get("value_score", 0), reverse=True)
        logger.info("✅ AI analysis complete!")

        return androids

    def _enrich_with_kimovil_specs(self, androids: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Enrich phones with comprehensive specs from Kimovil.com

        This dramatically improves scoring accuracy by using real specs instead of parsing titles.

        Args:
            androids: List of phone dictionaries

        Returns:
            Updated list with kimovil_specs field added
        """
        if not self.spec_enricher:
            logger.info("⏭️  Kimovil spec enrichment disabled")
            return androids

        logger.info("--- 🆕 ENRICHING WITH KIMOVIL SPECS ---")
        logger.info(f"📥 Fetching comprehensive specs for {len(androids)} phones...")

        # Run async enrichment (uses Playwright + SQLite cache)

        enriched_androids = asyncio.run(self.spec_enricher.enrich_phone_list(androids))

        # Count successes
        enriched_count = sum(1 for p in enriched_androids if p.get("kimovil_specs"))
        cache_hit_rate = (enriched_count / len(enriched_androids) * 100) if enriched_androids else 0

        logger.info(
            f"✅ Enriched {enriched_count}/{len(enriched_androids)} phones ({cache_hit_rate:.1f}%)"
        )
        logger.info("💾 Specs cached for future runs (instant lookup)")

        return enriched_androids

    def analyze_all_androids(self, use_session_dir: bool = True) -> list[dict[str, Any]]:
        """Analyze all Android phones with value scoring and optional AI analysis.

        This is the main orchestrator method that:
        1. Loads Android phone listings
        2. 🆕 Enriches with Kimovil specs (NEW Phase 3)
        3. Calculates value scores
        4. Fetches details for top phones
        5. Runs optional AI analysis (2-tier: Gemini + fallback)

        Args:
            use_session_dir: Whether to use session-based directory structure

        Returns:
            List of analyzed phone data dictionaries, sorted by value score
        """
        logger.info("=" * 80)
        logger.info("ANALYZING ALL ANDROID PHONES")
        logger.info("=" * 80)

        # Step 1: Load Android phones
        try:
            androids = (
                self._load_androids_from_session()
                if use_session_dir
                else self._load_androids_from_legacy()
            )
        except FileNotFoundError:
            return []

        logger.info(f"Total Android phones to analyze: {len(androids)}")

        # Step 2: 🆕 NEW Phase 3: Enrich with Kimovil specs (if enabled)
        if self.spec_enricher:
            androids = self._enrich_with_kimovil_specs(androids)

        # Step 3: Calculate value scores and sort
        self._calculate_all_scores(androids)

        # Step 4: Fetch full details for top phones
        top_count = min(len(androids), config.TOP_RECOMMENDATIONS_COUNT)
        androids = self._fetch_top_phone_details(androids, top_count)

        # Fetched descriptions feed condition, battery and warranty rules: re-score and re-sort
        for phone in androids[:top_count]:
            self.calculate_value_score(phone)
        androids.sort(key=lambda x: x.get("value_score", 0), reverse=True)

        # Step 5: AI analysis (optional 2-tier system)
        if (self.gemini and self.gemini.enabled) or (self.cloud_llm and self.cloud_llm.enabled):
            androids = self._run_ai_analysis_pipeline(androids, top_count)

        return androids

    # TODO: Implement real API spec fetching
    def fetch_specs_from_api(self, phone_model):
        """
        Fetch phone specifications from external APIs

        TODO: Integrate with:
        1. https://publicapi.dev/phone-specification-api
        2. https://phonedb.net/api (if available)
        3. github.com/epuerta9/whisk (Python library)

        For now, returns None (placeholder)
        """
        # PLACEHOLDER - Implement API calls here
        logger.debug(f"TODO: Fetch specs for {phone_model}")

    def _get_output_file_paths(self, use_session_dir: bool) -> dict[str, str]:
        """Determine output file paths based on configuration"""
        if use_session_dir:
            output_files = config.get_output_files()
            return {
                "analyzed": output_files["analyzed_androids"],
                "top": output_files["top_androids"],
                "report": output_files["recommendations_report"],
            }
        return {
            "analyzed": str(config.ANALYZED_ANDROIDS_FILE),
            "top": str(config.TOP_ANDROIDS_FILE),
            "report": str(config.RECOMMENDATIONS_REPORT),
        }

    def _save_full_analysis(self, androids: list[dict[str, Any]], output_path: str) -> None:
        """Save complete analysis results to JSON file"""
        with Path(output_path).open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "total": len(androids),
                    "analyzed_at": datetime.now().isoformat(),
                    "configuration": config.get_config_summary(),
                    "phones": androids,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        logger.info(f"✅ Saved full analysis: {config.display_path(output_path)}")

    def _save_top_phones(self, top_phones: list[dict[str, Any]], output_path: str) -> None:
        """Save top N phones to JSON file"""
        with Path(output_path).open("w", encoding="utf-8") as f:
            json.dump(
                {"count": len(top_phones), "phones": top_phones},
                f,
                ensure_ascii=False,
                indent=2,
            )
        logger.info(
            f"✅ Saved top {config.TOP_RECOMMENDATIONS_COUNT}: {config.display_path(output_path)}"
        )

    def _write_report_header(self, f, total_count: int, top_count: int) -> None:
        """Write report header section"""
        f.write("=" * 100 + "\n")
        f.write("🤖 TOP ANDROID PHONE RECOMMENDATIONS - VALUE ANALYSIS\n")
        f.write(f"Analyzed: {total_count} phones | Top picks: {top_count}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Location: {config.AVAILABLE_LOCATIONS.get(config.LOCATION, config.LOCATION)}\n")
        f.write(f"Price Range: {config.get_price_range_display()}\n")
        f.write("=" * 100 + "\n\n")

    def _write_phone_entry(self, f, phone: dict[str, Any], rank: int) -> None:
        """Write individual phone entry to report"""
        f.write(f"\n{'=' * 100}\n")
        f.write(f"RANK #{rank} | VALUE SCORE: {phone['value_score']} pts\n")
        f.write(f"{'=' * 100}\n\n")

        # Basic info (use normalized title if available)
        display_title = phone.get("normalized_title", phone["title"])
        f.write(f"📱 {display_title}\n")
        f.write(f"💰 PRICE: {phone['price']:,} KZT\n")

        # Market info
        if phone.get("market_initial_price"):
            f.write(f"💵 ORIGINAL PRICE: {phone['market_initial_price']:,} KZT\n")
            f.write(f"📉 DISCOUNT: {phone['discount_percent']:.0f}% OFF\n")
            f.write(f"📅 RELEASE YEAR: {phone.get('release_year', 'N/A')}\n")

        # Details
        f.write(f"🏷️  BRAND: {phone.get('detected_brand', 'Unknown').title()}\n")
        if phone.get("dxomark_score"):
            f.write(
                f"📸 CAMERA: DXOMark {phone['dxomark_score']} ({phone.get('camera_score', 0)} pts)\n"
            )
        f.write(f"📊 STATUS: {phone.get('status', 'N/A')}\n")
        f.write(f"📍 LOCATION: {phone.get('location', 'N/A')}\n")
        f.write(f"🔗 LINK: {phone['link']}\n")
        for warning in phone.get("warnings", []):
            f.write(f"⚠️  {warning}\n")
        f.write("\n")

        # Value factors
        if phone.get("value_factors"):
            f.write("⭐ VALUE FACTORS:\n")
            for factor in phone["value_factors"]:
                f.write(f"   {factor}\n")
            f.write("\n")

        # Gemini analysis
        if phone.get("gemini_analysis", {}).get("analyzed"):
            gemini_summary = self.gemini.get_analysis_summary(phone) if self.gemini else ""
            if gemini_summary:
                f.write(gemini_summary)
                f.write("\n")

        # Description
        if phone.get("description"):
            f.write("📝 DESCRIPTION:\n")
            desc = phone["description"][:MAX_DESCRIPTION_DISPLAY_LENGTH]
            max_len = MAX_DESCRIPTION_DISPLAY_LENGTH
            f.write(f"{desc}{'...' if len(phone['description']) > max_len else ''}\n\n")

    def save_results(
        self, androids: list[dict[str, Any]], use_session_dir: bool = True
    ) -> list[dict[str, Any]]:
        """Save analyzed results

        Args:
            androids: List of analyzed phone data
            use_session_dir: Whether to use session-based directory structure

        Returns:
            Top N recommendations list
        """
        logger.info("=" * 80)
        logger.info("SAVING ANALYSIS RESULTS")
        logger.info("=" * 80)

        # Log statistics
        gemini_analyzed = sum(1 for p in androids if p.get("gemini_analysis", {}).get("analyzed"))
        with_descriptions = sum(1 for p in androids if p.get("description"))
        with_views = sum(1 for p in androids if p.get("views", 0) > 0)

        logger.info(f"💾 Saving {len(androids)} phones:")
        logger.info(f"   - With Gemini analysis: {gemini_analyzed}")
        logger.info(f"   - With descriptions: {with_descriptions}")
        logger.info(f"   - With view counts: {with_views}")

        # Get output file paths
        paths = self._get_output_file_paths(use_session_dir)

        # Save full analysis and top N
        self._save_full_analysis(androids, paths["analyzed"])
        top_n = androids[: config.TOP_RECOMMENDATIONS_COUNT]
        self._save_top_phones(top_n, paths["top"])

        # Create human-readable report
        with Path(paths["report"]).open("w", encoding="utf-8") as f:
            self._write_report_header(f, len(androids), config.TOP_RECOMMENDATIONS_COUNT)
            for i, phone in enumerate(top_n, 1):
                self._write_phone_entry(f, phone, i)

        logger.info(f"✅ Saved report: {config.display_path(paths['report'])}")

        return top_n


def main():
    logger.info("=" * 80)
    logger.info("🔍 ADVANCED ANDROID PHONE ANALYZER")
    logger.info("Value analysis with market price comparison")
    logger.info("=" * 80)

    analyzer = AndroidAnalyzer()

    # Analyze all phones
    androids = analyzer.analyze_all_androids(use_session_dir=True)

    if not androids:
        logger.error("❌ No Android phones to analyze!")
        return

    # Save results
    top_n = analyzer.save_results(androids, use_session_dir=True)

    # Display top 10
    logger.info("=" * 80)
    logger.info("🏆 TOP 10 BEST VALUE ANDROID PHONES")
    logger.info("=" * 80)

    for i, phone in enumerate(top_n[:10], 1):
        logger.info(f"\n#{i} | Score: {phone['value_score']} pts | {phone['price']:,} KZT")
        logger.info(f"    {phone['title'][:75]}")

        if phone.get("discount_percent"):
            logger.info(
                f"    💎 {phone['discount_percent']:.0f}% OFF (was {phone['market_initial_price']:,} KZT)"
            )

        if phone.get("value_factors"):
            logger.info(f"    ⭐ {' | '.join(phone['value_factors'][:3])}")

        logger.info(f"    🔗 {phone['link']}")

    logger.info("✅ Analysis completed successfully!")

    logger.info("--- TODO FOR FUTURE IMPROVEMENTS ---")
    logger.info("  1. [ ] Integrate Phone Specification API (publicapi.dev)")
    logger.info("  2. [ ] Add PhoneDB.net integration")
    logger.info("  3. [ ] Install and use 'whisk' library (github.com/epuerta9/whisk)")
    logger.info("  4. [ ] Fetch real-time market prices from e-commerce APIs")
    logger.info("  5. [ ] Add comparison with similar models")
    logger.info("  6. [ ] Implement AnTuTu/Geekbench score lookup")

    # Log file info
    logger.info(f"\n📊 Logs saved to: {config.get_logs_dir()}")

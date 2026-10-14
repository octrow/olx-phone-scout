#!/usr/bin/env python3
"""
olx-phone-scout - Main Entry Point (Unified Async Pipeline)
======================================================================

All-in-one async pipeline that orchestrates:
1. Async scraping (10-30x faster than sync)
2. Re-categorization with improved brand detection
3. Async details fetching (15-40x faster)
4. Value score calculation
5. Async AI analysis (optional, 3-8x faster)
6. Results saving and reporting

Usage:
    python main.py                  # Full pipeline
    python main.py --scrape-only    # Scrape only
    python main.py --analyze-only   # Analyze existing data
    python main.py --gemini         # With Gemini AI
    python main.py --cerebras       # With Cerebras (ultra-fast)
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime

from src.analysis.analyzer import AndroidAnalyzer
from src.core import config
from src.core.async_scraper import AsyncOLXScraper
from src.detection.recategorize import detect_phone_brand_improved
from src.infrastructure import logging as logging_cfg
from src.infrastructure.logging import logger
from src.infrastructure.setup_env import setup_env

# =============================================================================
# STEP 1: ASYNC SCRAPING
# =============================================================================


async def run_scraper(args):
    """
    Step 1: Async scraping (10-30x faster than sync)
    Returns: (iphones, androids, unknown) or ([], [], []) on failure
    """
    logger.info("=" * 80)
    logger.info("STEP 1: ASYNC SCRAPING OLX.KZ")
    logger.info("=" * 80)

    try:
        # Setup parameters
        min_price = (
            args.min_price if hasattr(args, "min_price") and args.min_price else config.MIN_PRICE
        )
        max_price = (
            args.max_price if hasattr(args, "max_price") and args.max_price else config.MAX_PRICE
        )
        max_pages = (
            args.max_pages if hasattr(args, "max_pages") and args.max_pages else config.MAX_PAGES
        )
        days_back = (
            args.days_back if hasattr(args, "days_back") and args.days_back else config.DAYS_BACK
        )

        # Show configuration
        location_name = config.AVAILABLE_LOCATIONS.get(config.LOCATION, config.LOCATION)
        logger.info(f"🎯 Target: Phones in {location_name}, {min_price:,} - {max_price:,} KZT")
        logger.info(f"📅 Timeline: Last {days_back} days | Max pages: {max_pages}")
        logger.info("")

        async with AsyncOLXScraper() as scraper:
            # Scrape all pages concurrently
            new_listings = await scraper.scrape_listing_cards(
                min_price=min_price,
                max_price=max_price,
                max_pages=max_pages,
                days_back=days_back,
            )

            if not new_listings:
                logger.warning("⚠️  No new listings found!")
                return [], [], []

            logger.info(f"✅ Found {len(new_listings)} new listings")

            # Merge with existing
            all_listings = scraper.merge_with_existing(use_session_dir=True)

            # Save and categorize
            iphones, androids, unknown = scraper.save_results(all_listings, use_session_dir=True)

            logger.info("")
            logger.info("SCRAPING COMPLETE:")
            logger.info(f"  • Total:    {len(all_listings):4d}")
            logger.info(
                f"  • iPhones:  {len(iphones):4d} ({len(iphones) / len(all_listings) * 100:.1f}%)"
            )
            logger.info(
                f"  • Android:  {len(androids):4d} ({len(androids) / len(all_listings) * 100:.1f}%)"
            )
            logger.info(
                f"  • Unknown:  {len(unknown):4d} ({len(unknown) / len(all_listings) * 100:.1f}%)"
            )
            logger.info("")

            return iphones, androids, unknown

    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}", exc_info=True)
        return [], [], []


# =============================================================================
# STEP 2: RE-CATEGORIZATION
# =============================================================================


def run_recategorization():
    """
    Step 2: Re-categorize with improved brand detection
    Returns: (iphones, androids, unknown) or ([], [], []) on failure
    """
    logger.info("=" * 80)
    logger.info("STEP 2: RE-CATEGORIZING LISTINGS")
    logger.info("=" * 80)

    try:
        # Load from session directory
        data_file = config.get_output_files()["all_listings"]

        if not data_file.exists():
            logger.warning("⚠️  No listings file found. Skipping recategorization.")
            return [], [], []

        with data_file.open(encoding="utf-8") as f:
            data = json.load(f)

        all_listings = data.get("listings", [])
        logger.info(f"📊 Re-categorizing {len(all_listings)} listings...")

        # Re-categorize with improved detection
        iphones = []
        androids = []
        unknown = []

        for listing in all_listings:
            brand, phone_type = detect_phone_brand_improved(listing["title"])
            listing["detected_brand"] = brand
            listing["phone_type"] = phone_type

            if phone_type == "iphone":
                iphones.append(listing)
            elif phone_type == "android":
                androids.append(listing)
            else:
                unknown.append(listing)

        # Save updated data
        output_files = config.get_output_files()

        with output_files["all_listings"].open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "total": len(all_listings),
                    "scraped_at": data.get("scraped_at", datetime.now().isoformat()),
                    "listings": all_listings,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        with output_files["iphones"].open("w", encoding="utf-8") as f:
            json.dump({"count": len(iphones), "phones": iphones}, f, ensure_ascii=False, indent=2)

        with output_files["androids"].open("w", encoding="utf-8") as f:
            json.dump({"count": len(androids), "phones": androids}, f, ensure_ascii=False, indent=2)

        with output_files["unknown"].open("w", encoding="utf-8") as f:
            json.dump({"count": len(unknown), "phones": unknown}, f, ensure_ascii=False, indent=2)

        logger.info("")
        logger.info("RE-CATEGORIZATION COMPLETE:")
        logger.info(
            f"  • iPhones:  {len(iphones):4d} ({len(iphones) / len(all_listings) * 100:.1f}%)"
        )
        logger.info(
            f"  • Android:  {len(androids):4d} ({len(androids) / len(all_listings) * 100:.1f}%)"
        )
        logger.info(
            f"  • Unknown:  {len(unknown):4d} ({len(unknown) / len(all_listings) * 100:.1f}%)"
        )
        logger.info("")

        return iphones, androids, unknown

    except Exception as e:
        logger.error(f"❌ Re-categorization failed: {e}", exc_info=True)
        return [], [], []


# =============================================================================
# STEP 3: ASYNC ANALYSIS
# =============================================================================


async def run_analyzer(  # noqa: PLR0913
    use_gemini=False,
    gemini_use_photos=False,
    use_cerebras=False,
    use_openrouter=False,
    max_details=100,
    max_ai_analysis=30,
):
    """
    Step 3: Analysis pipeline using AndroidAnalyzer
    - Uses analyzer.analyze_all_androids() which includes:
      * Value score calculation
      * Details fetching for top phones
      * AI analysis (Gemini + fallback)
    Returns: True on success, False on failure
    """
    logger.info("=" * 80)
    logger.info("STEP 3: ANALYZING ANDROID PHONES")
    logger.info("=" * 80)

    try:
        # Initialize analyzer with AI options
        logger.info("Initializing analyzer with AI options...")
        analyzer = AndroidAnalyzer(
            use_gemini=use_gemini,
            gemini_use_photos=gemini_use_photos,
            gemini_top_n=max_ai_analysis if use_gemini else None,
            reset_gemini_cache=False,
            gemini_async=False,
            use_cerebras=use_cerebras,
            cerebras_model="fast",
            use_openrouter=use_openrouter,
            openrouter_model="fast",
        )

        # Run full analysis pipeline (scores ALL phones, fetches details for top N, runs AI)
        logger.info("Running full analysis pipeline...")
        androids = await asyncio.to_thread(analyzer.analyze_all_androids, use_session_dir=True)

        if not androids:
            logger.warning("⚠️  No Android phones to analyze!")
            return False

        # Save results & generate report
        logger.info("")
        logger.info("SAVING RESULTS & GENERATING REPORT")
        top_phones = analyzer.save_results(androids, use_session_dir=True)

        # Show top 5
        logger.info("")
        logger.info("🏆 TOP 5 BEST VALUE PHONES:")
        for i, phone in enumerate(top_phones[:5], 1):
            score = phone.get("value_score", 0)
            price = phone.get("price", 0)
            title = phone.get("title", "Unknown")[:60]
            discount = phone.get("discount_percent", 0)

            logger.info(f"\n  #{i} | Score: {score:.1f} pts | {price:,} KZT")
            logger.info(f"      {title}")
            if discount and discount > 0:
                logger.info(f"      💎 {discount:.0f}% OFF market price")
            for warning in phone.get("warnings", []):
                logger.warning(f"      ⚠️  {warning}")

        logger.info("")
        return True

    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}", exc_info=True)
        return False


# =============================================================================
# MAIN ASYNC PIPELINE
# =============================================================================


async def run_pipeline(args):
    """
    Main async pipeline - orchestrates all steps
    Returns: dict with results of each step
    """
    logger.info("🚀" * 40)
    logger.info("OLX PHONE SCOUT - UNIFIED ASYNC PIPELINE")
    logger.info("🚀" * 40)
    logger.info(f"Session: {config.get_session_name()}")
    if config.INCLUDE_BUSINESS:
        logger.warning("⚠️  Shops included: listings from resellers are marked 🏪 in the results")
    if config.LOCATION != "alma-ata":
        logger.warning(
            f"⚠️  Searching {config.AVAILABLE_LOCATIONS.get(config.LOCATION, config.LOCATION)}: "
            f"listings outside {config.HOME_CITY} are marked 📍 in the results"
        )
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")

    results = {}

    try:
        # Determine what to run
        run_all = args.all if hasattr(args, "all") else False
        scrape = run_all or (hasattr(args, "scrape") and args.scrape)
        recategorize = run_all or (hasattr(args, "recategorize") and args.recategorize)
        analyze = run_all or (hasattr(args, "analyze") and args.analyze)

        # Default behavior: run everything
        if not (scrape or recategorize or analyze):
            scrape = recategorize = analyze = True

        # STEP 1: Scrape
        if scrape:
            iphones, androids, unknown = await run_scraper(args)
            results["scrape"] = len(androids) > 0
        else:
            logger.info("⏭️  Skipping scraping (using existing data)")

        # STEP 2: Re-categorize
        if recategorize:
            iphones, androids, unknown = run_recategorization()  # noqa: RUF059
            results["recategorize"] = len(androids) > 0

        # STEP 3: Analyze
        if analyze:
            success = await run_analyzer(
                use_gemini=getattr(args, "gemini", False),
                gemini_use_photos=getattr(args, "gemini_photos", False),
                use_cerebras=getattr(args, "cerebras", False),
                use_openrouter=getattr(args, "openrouter", False),
                max_ai_analysis=getattr(args, "gemini_top_n", 30),
            )
            results["analyze"] = success

        # Final summary
        logger.info("=" * 80)
        logger.info("EXECUTION SUMMARY")
        logger.info("=" * 80)

        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)

        logger.info(f"Operations completed: {success_count}/{total_count}")

        for operation, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            logger.info(f"  • {operation.title()}: {status}")

        logger.info("")
        logger.info(f"📂 Session directory: {config.display_path(config.get_session_dir())}")
        logger.info(f"📊 Results: {config.display_path(config.get_results_dir())}")
        logger.info("")

        if success_count == total_count and total_count > 0:
            logger.info("✅ ALL OPERATIONS COMPLETED SUCCESSFULLY! 🎉")
            return True
        if success_count > 0:
            logger.warning(f"⚠️  Completed with some failures ({success_count}/{total_count})")
            return False
        logger.error("❌ ALL OPERATIONS FAILED")
        return False

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Pipeline interrupted by user")
        return False
    except Exception as e:
        logger.error(f"❌ Pipeline error: {e}", exc_info=True)
        return False


# =============================================================================
# CLI & MAIN
# =============================================================================


CLI_CONFIG_OVERRIDES = {
    "min_price": "MIN_PRICE",
    "max_price": "MAX_PRICE",
    "max_pages": "MAX_PAGES",
    "days_back": "DAYS_BACK",
    "phone_type": "PHONE_TYPE_FILTER",
    "location": "LOCATION",
    "include_business": "INCLUDE_BUSINESS",
}


def apply_cli_overrides(args) -> None:
    """Write CLI values into config so session dir, scraper and analyzer all see them."""
    for arg_name, config_name in CLI_CONFIG_OVERRIDES.items():
        value = getattr(args, arg_name, None)
        if value is not None:
            setattr(config, config_name, value)
    if not config.validate_config():  # logs each error itself
        raise SystemExit(2)


def main():
    setup_env()
    parser = argparse.ArgumentParser(
        description="olx-phone-scout - Unified Async Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline
  python main.py

  # Individual steps
  python main.py --scrape
  python main.py --recategorize
  python main.py --analyze

  # With AI analysis
  python main.py --analyze --gemini
  python main.py --analyze --cerebras
  python main.py --analyze --openrouter

  # Custom price range
  python main.py --min-price 150000 --max-price 300000

  # Show configuration
  python main.py --show-config
        """,
    )

    # Operation modes
    parser.add_argument(
        "--all", action="store_true", help="Run full pipeline (scrape -> recategorize -> analyze)"
    )
    parser.add_argument("--scrape", action="store_true", help="Run scraper only")
    parser.add_argument("--recategorize", action="store_true", help="Run recategorization only")
    parser.add_argument("--analyze", action="store_true", help="Run analyzer only")

    # Scraper parameters
    parser.add_argument(
        "--min-price", type=int, help=f"Minimum price (default: {config.MIN_PRICE} KZT)"
    )
    parser.add_argument(
        "--max-price", type=int, help=f"Maximum price (default: {config.MAX_PRICE} KZT)"
    )
    parser.add_argument(
        "--max-pages", type=int, help=f"Maximum pages to scrape (default: {config.MAX_PAGES})"
    )
    parser.add_argument(
        "--days-back", type=int, help=f"Days back to search (default: {config.DAYS_BACK})"
    )
    parser.add_argument(
        "--location",
        choices=sorted(config.AVAILABLE_LOCATIONS),
        help=f"OLX location slug (default: {config.LOCATION}; 'alm' = Almaty city + region)",
    )
    parser.add_argument(
        "--include-business",
        action="store_true",
        default=None,
        help="Include shops/resellers (default: private sellers only)",
    )
    parser.add_argument(
        "--phone-type",
        choices=["android", "iphone", "both"],
        help=f"Phones to analyze (default: {config.PHONE_TYPE_FILTER})",
    )

    # AI parameters
    parser.add_argument("--gemini", action="store_true", help="Use Gemini AI for analysis")
    parser.add_argument(
        "--gemini-photos", action="store_true", help="Upload photos to Gemini (uses more tokens)"
    )
    parser.add_argument(
        "--gemini-top-n",
        type=int,
        default=30,
        help="Number of top phones to analyze with Gemini (default: 30)",
    )
    parser.add_argument(
        "--cerebras", action="store_true", help="Use Cerebras (ultra-fast, 2000-3000 tokens/sec)"
    )
    parser.add_argument("--openrouter", action="store_true", help="Use OpenRouter (free models)")

    # Configuration
    parser.add_argument("--show-config", action="store_true", help="Show configuration and exit")

    args = parser.parse_args()
    apply_cli_overrides(args)
    # After overrides: the session name (and so the logs dir) depends on price range + phone type.
    logging_cfg.configure_logging(app_name="olx_analyzer", level="INFO")

    # Show config and exit
    if args.show_config:
        config.print_config()
        return 0

    # Run async pipeline
    try:
        success = asyncio.run(run_pipeline(args))
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

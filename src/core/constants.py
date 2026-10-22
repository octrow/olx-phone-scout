#!/usr/bin/env python3
"""
Global Constants for OLX Phone Analyzer
========================================
Centralized constants to avoid magic numbers and strings throughout the codebase.
"""

# HTTP/Network Constants
DEFAULT_REQUEST_TIMEOUT = 15  # seconds
DEFAULT_REQUEST_DELAY = 1.5  # seconds between requests
MAX_RETRIES = 3
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Scraping Constants
DEFAULT_MAX_PAGES = 20
DEFAULT_DAYS_BACK = 25
LISTINGS_PER_PAGE = 15  # Approximate

# Third-party API/Scraping Constants
KIMOVIL_REQUEST_DELAY = 2.5
KIMOVIL_MAX_CONCURRENT = 2
KIMOVIL_FETCH_TIMEOUT_S = 20  # curl_cffi page fetch

# File Size Limits
MAX_LOG_FILE_SIZE_MB = 50
MAX_LOG_BACKUPS = 20
LOG_RETENTION_DAYS = 7

# Analysis Constants
DEFAULT_TOP_RECOMMENDATIONS = 50
ALERT_TOP_N = 10  # --notify: top listings checked for new ones
MIN_BRAND_CONFIDENCE_SCORE = 50
MAX_FUNCTION_COMPLEXITY = 15
MAX_FUNCTION_STATEMENTS = 50
BATTERY_CAPACITY = 5000

# Scoring Weights (0-100 scale)
MAX_DISCOUNT_SCORE = 50
# Discount sanity check: a used phone N years old rarely sells for more than
# BASE + PER_YEAR * N percent off launch price; beyond that it's a copy, scam or for parts.
PLAUSIBLE_DISCOUNT_BASE = 65
PLAUSIBLE_DISCOUNT_PER_YEAR = 6
PLAUSIBLE_DISCOUNT_CAP = 92
SUSPICIOUS_DISCOUNT_PENALTY = 80
MAX_AGE_SCORE = 30
MAX_TIER_SCORE = 55
MAX_STORAGE_SCORE = 34
MAX_RAM_SCORE = 26
MAX_PRICE_RANGE_SCORE = 25
MAX_CONDITION_SCORE = 20
MAX_BRAND_SCORE = 30
MAX_CAMERA_SCORE = 50

# screen hz
HZ_90 = 90
HZ_120 = 120
HZ_144 = 144
HZ_160 = 160

# Phone Categories
PHONE_TYPE_IPHONE = "iphone"
PHONE_TYPE_ANDROID = "android"
PHONE_TYPE_UNKNOWN = "unknown"

# Phone Status
STATUS_NEW = "Новый"
STATUS_USED = "Б/у"

# Currency
CURRENCY_KZT = "KZT"
USD_TO_KZT_RATE = 533.51  # As of 29.10.2025
EUR_TO_KZT_RATE = 621.60  # As of 29.10.2025

# API Rate Limits
GEMINI_REQUESTS_PER_MINUTE = 15
GEMINI_TOKENS_PER_MINUTE = 1_000_000
GEMINI_REQUESTS_PER_DAY = 1500

# Time Constants
SECONDS_PER_DAY = 86400
CURRENT_YEAR = 2025

# File Extensions
JSON_EXTENSION = ".json"
TEXT_EXTENSION = ".txt"
LOG_EXTENSION = ".log"

# Progress Tracking
PROGRESS_UPDATE_INTERVAL = 50  # Update progress every N items
CHECKPOINT_SAVE_INTERVAL = 10  # Save checkpoint every N items
MAX_DESCRIPTION_DISPLAY_LENGTH = 500  # Max chars to display in reports
MAX_FAILED_PHONES_DISPLAY = 10  # Max number of failed phone indices to show

# Thresholds and Limits
MIN_CONFIDENCE_SCORE = 0  # Minimum brand confidence score
MAX_CONFIDENCE_SCORE = 100  # Maximum brand confidence score
LOG_SIZE_WARNING_MB = 150  # Warn when logs exceed this size in MB
API_KEY_MIN_LENGTH = 12  # Minimum API key length for masking
API_KEY_MASK_PREFIX = 8  # Characters to show at start when masking API key
API_KEY_MASK_SUFFIX = 4  # Characters to show at end when masking API key

# Session Management
SESSION_NAME_SEPARATOR = "_"
TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
COMPACT_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# Time Ranges (in days)
DAYS_YESTERDAY = 1
DAYS_RECENT_MIN = 2
DAYS_RECENT_MAX = 6
DAYS_ONE_WEEK = 7
DAYS_TWO_WEEKS = 14
DAYS_ONE_MONTH = 30

# Price Ranges (KZT)
PRICE_RANGE_30K = 30000
PRICE_RANGE_40K = 40000
PRICE_RANGE_50K = 50000
PRICE_RANGE_60K = 60000
PRICE_RANGE_70K = 70000
PRICE_RANGE_80K = 80000
PRICE_RANGE_90K = 90000
PRICE_RANGE_100K = 100000
PRICE_RANGE_110K = 110000
PRICE_RANGE_120K = 120000
PRICE_RANGE_130K = 130000
PRICE_RANGE_140K = 140000
PRICE_RANGE_150K = 150000

# Percentages
PERCENT_10 = 10
PERCENT_20 = 20
PERCENT_30 = 30
PERCENT_40 = 40
PERCENT_50 = 50
PERCENT_60 = 60
PERCENT_70 = 70
PERCENT_80 = 80
PERCENT_90 = 90
PERCENT_100 = 100

# HTTP Status Codes
HTTP_OK = 200

# Listing Details
MIN_SPANS_FOR_PARAM = 2  # Minimum number of spans required for parameter extraction

# Data Quality
MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 500
MIN_DESCRIPTION_LENGTH = 10
MAX_DESCRIPTION_LENGTH = 5000

# Image Processing
MAX_IMAGE_SIZE_MB = 5
SUPPORTED_IMAGE_FORMATS = ["jpg", "jpeg", "png", "webp"]
MAX_PHOTOS_PER_LISTING = 10

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# UI Constants
TERMINAL_WIDTH = 100
SECTION_SEPARATOR = "=" * TERMINAL_WIDTH
SUBSECTION_SEPARATOR = "-" * TERMINAL_WIDTH

# Error Messages
ERROR_NO_LISTINGS = "No listings found!"
ERROR_FILE_NOT_FOUND = "File not found: {}"
ERROR_INVALID_CONFIG = "Invalid configuration: {}"
ERROR_API_FAILURE = "API request failed: {}"
ERROR_NETWORK_TIMEOUT = "Network timeout after {} seconds"

# Success Messages
SUCCESS_SCRAPING_COMPLETE = "Scraping completed successfully!"
SUCCESS_ANALYSIS_COMPLETE = "Analysis completed successfully!"
SUCCESS_FILE_SAVED = "File saved: {}"

# Warning Messages
WARNING_NO_MARKET_DATA = "No market price data available for: {}"
WARNING_LOW_CONFIDENCE = "Low confidence brand detection: {}"
WARNING_RATE_LIMIT = "Rate limit approaching, slowing down..."

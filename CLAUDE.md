# olx-phone-scout

**AI-powered web scraper and analyzer for finding best phone deals on OLX.kz (Almaty, Kazakhstan)**

## Business Context

- **Purpose:** Find best value used phones on OLX.kz marketplace
- **Target market:** Almaty, Kazakhstan | Configurable price range (default: 100k-400k KZT)
- **Primary use case:** Automated phone deal hunting with AI analysis
- **Value proposition:**
  - Typo-tolerant brand detection (98.1% accuracy)
  - Market price comparison & value scoring
  - AI-powered defect detection (Gemini API)
  - Async/Sync modes (20-50x performance difference)
  - Session-based data management

---

## Quick Start

### Option 1: Simple Run (Recommended)
```bash
./run.sh                    # Full pipeline (async, 20-50x faster!)
./run.sh --scrape           # Scrape only
./run.sh --analyze          # Analyze existing data
./run.sh --gemini           # With Gemini AI analysis
./run.sh --cerebras         # With Cerebras (ultra-fast)
```

### Option 2: Direct Python
```bash
# 1. Setup environment
uv sync                                  # deps + dev group (pytest, ruff, mypy)

# 2. Run unified async pipeline
uv run main.py              # Full pipeline
uv run main.py --help       # See all options
```

### Configuration
Edit `src/core/config.py` to customize:
- Location (LOCATION = "alma-ata")
- Price range (MIN_PRICE, MAX_PRICE)
- Search depth (MAX_PAGES, DAYS_BACK)
- Phone type (PHONE_TYPE_FILTER = "android")

---

## Architecture Overview

### Execution Flow

```
run.sh
  └─> main.py (entry point)
      └─> run_pipeline() (UNIFIED ASYNC PIPELINE)
          ├─> run_scraper()          Step 1: async scraping (concurrent pages)
          ├─> run_recategorization() Step 2: re-categorization (brand detection)
          └─> run_analyzer()         Step 3: details fetching, Kimovil specs,
                                             value scoring, optional AI, rankings
```

### Key Components

**1. Web Scraping**
- `src/core/async_scraper.py` - Async scraper (PoliteClient from `market-sources`: paced + retrying)
- `src/core/browser_transport.py` - httpx transport over curl_cffi with Chrome TLS fingerprint
  (OLX's CloudFront returns 403 to httpx's own TLS handshake, whatever the headers)
- `src/fetchers/listing_fetcher.py` - Async listing details fetcher (same transport)
- OLX caps every search at 1000 results (25 pages): `_price_slices` halves the price range until
  each slice is under the cap, then fetches every page of every slice
- Analyzer loads fresh `androids.json`/`iphones.json` each run and reuses cached descriptions from
  `androids_analyzed.json` by link
- Typo-tolerant brand detection (22 brands, Cyrillic support)
- Configurable search parameters

**2. Brand Detection**
- `src/detection/patterns.py` - 22 brands with regex patterns
- `src/detection/recategorize.py` - Re-categorization utility
- 98.1% accuracy (unknown rate: 1.9%)
- Supports typos: "xioami" → Xiaomi, "techno" → Tecno

**3. Value Analysis**
- `src/analysis/analyzer.py` - Main analyzer
- `src/analysis/scoring.py` - Scoring rules & weights
- `src/analysis/market_data.py` - Market price database (102 models)
- Multi-factor scoring: discount, age, specs, condition

**4. AI Integration**
- `src/ai/gemini.py` - Google Gemini API (async-ready)
- `src/ai/cloud_llm.py` - Cerebras/OpenRouter/Vercel (async batch processing)
- Defect detection & bonus feature extraction
- Caching system (avoid duplicate API calls)

**5. Session Management**
- `src/core/config.py` - Centralized configuration
- Session-based directories (all data in one place)
- Automatic session naming: `{location}_{priceRange}_{phoneType}`

**6. Spec Enrichment (Kimovil)**
- `src/enrichment/kimovil_scraper.py` - curl_cffi fetches the page (Chrome TLS fingerprint), selectolax
  parses it (no browser); global SQLite cache (`data/cache/kimovil_specs.db`)
- Table labels repeat across sections ("Type", "Resolution", "Capacity"): the first row wins (screen,
  storage); a "Capacity" in mAh goes to `battery_capacity`
- `src/enrichment/spec_enrichment.py` - Title → (brand, model), enriches phone list
- Rate limiting: one scrape per model per run, at most `KIMOVIL_MAX_CONCURRENT` concurrent fetches,
  `KIMOVIL_REQUEST_DELAY` between requests (both in `src/core/constants.py`)
- Only successful scrapes are cached; failures are retried on the next run

**7. Pipeline**
- `main.py` - Entry point: CLI, logging, pipeline steps
- `run.sh` - Convenience wrapper

---

## Project Structure

```
/olx-phone-scout/
├── run.sh                          # Main entry point (wrapper)
├── main.py                         # Entry point (CLI + pipeline steps)
├── tests/                          # pytest (`uv run pytest`)
│
├── src/                            # Core source code
│   ├── core/                       # Core functionality
│   │   ├── config.py              # Centralized configuration
│   │   ├── constants.py           # Constants
│   │   ├── async_scraper.py       # Async OLX scraper
│   │   └── browser_transport.py   # curl_cffi transport (Chrome TLS fingerprint)
│   │
│   ├── detection/                  # Brand detection
│   │   ├── patterns.py            # Brand patterns (22 brands)
│   │   └── recategorize.py        # Re-categorization utility
│   │
│   ├── analysis/                   # Value analysis
│   │   ├── analyzer.py            # Main analyzer
│   │   ├── scoring.py             # Scoring algorithm
│   │   └── market_data.py         # Market prices (102 models)
│   │
│   ├── ai/                         # AI integration
│   │   ├── gemini.py              # Google Gemini API
│   │   └── cloud_llm.py           # Cerebras/OpenRouter/Vercel
│   │
│   ├── enrichment/                 # Kimovil specs
│   │   ├── kimovil_scraper.py     # curl_cffi + selectolax scraper, SQLite cache
│   │   └── spec_enrichment.py     # Brand/model extraction + enrichment
│   │
│   ├── fetchers/                   # Listing details
│   │   ├── listing_fetcher.py     # Async details fetcher
│   │   └── listing_parser.py      # Details HTML parser
│   │
│   └── infrastructure/             # Infrastructure
│       ├── logging.py             # Loguru-based logging
│       ├── alerts.py              # --notify: Telegram alerts for new top listings
│       ├── cache.py               # Disk caching
│       └── setup_env.py           # Environment setup
│
├── data/sessions/                  # Session-specific data
│   └── {session_name}/             # e.g., alma-ata_100k-400k_android
│       ├── results/                # JSON outputs
│       ├── reports/                # TXT reports
│       ├── logs/                   # Log files
│       └── cache/                  # Cache (Gemini, specs, etc.)
│
├── README.md / README.ru.md        # User documentation (EN / RU mirror)
└── CLAUDE.md                       # This file (AI entry point)
```

---

## Data Flow

### 1. Scraping
```
OLX.kz → AsyncOLXScraper (src/core/async_scraper.py) → all_listings.json
  • Extract: title, price, location, link, image
  • Detect: brand, phone_type (iPhone/Android/Unknown)
  • Deduplicate by URL
  • Save to: data/sessions/{session}/results/
```

### 2. Categorization
```
all_listings.json → src/detection/recategorize.py → {androids, iphones, unknown}.json
  • Re-apply improved brand patterns
  • Separate by phone type
  • Calculate: iPhones (65%), Androids (33%), Unknown (2%)
```

### 3. Analysis
```
androids.json → AndroidAnalyzer → androids_analyzed.json → TOP_50_ANDROID.json
  • Calculate value scores (multi-factor)
  • Fetch listing details (description, photos)
  • AI analysis (optional): defects, bonuses
  • Sort by score, save top N
```

### 4. Reporting
```
TOP_50_ANDROID.json → generate_report() → TOP_RECOMMENDATIONS_{timestamp}.txt
  • Human-readable format
  • Pros/cons, AI insights
  • Discount calculations
  • Ranking by value score
```

---

## Session Management

**Every run creates or uses a session:**

Session Name Format: `{location}_{priceRange}_{phoneType}`
Example: `alma-ata_100k-400k_android`

**Session Directory Structure:**
```
data/sessions/alma-ata_100k-400k_android/
├── results/                    # All JSON data
│   ├── all_listings.json      # All scraped listings
│   ├── androids.json          # Android phones
│   ├── iphones.json           # iPhones
│   ├── unknown.json           # Unknown phones
│   ├── androids_analyzed.json # With scores & AI analysis
│   └── TOP_50_ANDROID.json    # Top recommendations
│
├── reports/                    # All text reports
│   └── TOP_RECOMMENDATIONS_{timestamp}.txt
│
├── logs/                       # All log files
│   ├── run_all.log            # Main orchestrator
│   ├── scraper.log            # Scraping activity
│   ├── recategorize.log       # Brand detection
│   ├── analyzer.log           # Value analysis
│   └── gemini_api.log         # AI API calls
│
├── gemini_cache/               # AI response cache
│   ├── responses.json         # Cached API responses
│   └── checkpoint.json        # Progress tracking
│
└── session_info.json           # Session metadata
```

---

## Key Features

### 1. Typo-Tolerant Brand Detection
- **Accuracy:** 98.1% (unknown rate: 1.9%)
- **Brands:** 22 (Samsung, Xiaomi, Redmi, POCO, OPPO, etc.)
- **Languages:** English + Cyrillic (Russian/Kazakh)
- **Typo Patterns:**
  - "xioami" → Xiaomi
  - "techno" → Tecno
  - "poko" → POCO
  - "z фолд" → Samsung Z Fold

### 2. Value Scoring Algorithm
```
Total Score =
  + Discount (0-40 pts)        # Discount % from market price
  + Age Factor (0-30 pts)      # Phone release year
  + Tier Bonus (0-35 pts)      # Flagship/mid/budget
  + Storage (0-15 pts)         # 128GB/256GB/512GB
  + RAM (0-10 pts)             # 6GB/8GB/12GB+
  + Camera (0-32 pts)          # DXOMark score
  + Condition (0-20 pts)       # "excellent", "good", etc.
  + Price Range (0-25 pts)     # Within target range
```

### 3. AI Analysis (Optional)
- **Gemini API:** Defect detection, feature extraction
- **Free LLMs:** Cerebras, OpenRouter, Vercel
- **Photo Analysis:** Condition assessment from images
- **Caching:** Avoid duplicate API calls
- **Rate Limiting:** Respect API quotas

### 4. Async Mode (20-50x Faster)
- **Concurrent scraping:** Multiple pages simultaneously
- **Concurrent details fetching:** Batch API calls
- **Semaphore control:** Prevent rate limiting
- **Progress bars:** Real-time ETA with tqdm

---

## Configuration Reference

**File:** `config.py`

### Scraping Settings
```python
LOCATION = "alma-ata"  # OLX region
MIN_PRICE = 100000  # Min price (KZT)
MAX_PRICE = 400000  # Max price (KZT)
MAX_PAGES = 25  # Pages per price slice (OLX max)
DAYS_BACK = 25  # Search timeline
PHONE_TYPE_FILTER = "android"  # android/iphone/both
```

### Analysis Settings
```python
TOP_RECOMMENDATIONS_COUNT = 50  # How many results
REQUIRE_MARKET_DATA = False  # Allow unknown models
MIN_VALUE_SCORE = 50  # Minimum score threshold
MIN_BRAND_CONFIDENCE = 50  # Brand detection threshold
```

### Logging Settings
```python
LOG_LEVEL = "DEBUG"  # DEBUG/INFO/WARNING/ERROR
MAX_LOG_FILE_SIZE = 50  # MB per log file
MAX_LOG_BACKUPS = 20  # Number of backup files
LOG_RETENTION_DAYS = 7  # Auto-cleanup threshold
```

---

## Common Operations

### Full Pipeline
```bash
./run.sh                        # Full pipeline (async)
python main.py                  # Direct Python execution
```

### Individual Steps
```bash
# Scraping only
./run.sh --scrape

# Analysis only (use existing data)
./run.sh --analyze

# With AI analysis
./run.sh --gemini               # Google Gemini AI
./run.sh --cerebras             # Cerebras (ultra-fast)
./run.sh --openrouter           # OpenRouter (free models)

# Custom price range
./run.sh --min-price 150000 --max-price 300000

# Android + iPhone (session: alma-ata_15k-80k_both)
./run.sh --min-price 15000 --max-price 80000 --phone-type both

# Daily run: Telegram alert for listings new to the top 10 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
# Sent links per session: data/sessions/{session}/alerts_sent.json (src/infrastructure/alerts.py)
./run.sh --notify

# Wider search: Almaty city + region, shops too (session suffix _shops)
# Out-of-town (📍) and shop (🏪) listings get warnings, not score changes
./run.sh --location alm --include-business
```

### Tests
```bash
uv run pytest                   # all tests (+ coverage report in htmlcov/)
uv run pytest tests/test_kimovil_concurrency.py
```

### View Results
```bash
# Latest report
ls -lt data/sessions/*/reports/*.txt | head -1 | xargs cat

# Top 10 phones (JSON)
jq '.phones[0:10]' data/sessions/*/results/TOP_50_ANDROID.json

# Unknown phones
jq '.phones[].title' data/sessions/*/results/unknown.json
```

---

## Documentation Index

- **README.md** / **README.ru.md** - Installation & usage (keep the two in sync)
- **CONTRIBUTING.md** - Dev setup, PR rules
- **CHANGELOG.md** - Release notes
- **CLAUDE.md** - This file (AI entry point)

---

## Context Routing

**Where to find what:**

| Need | File | Location |
|------|------|----------|
| **Main pipeline** | `main.py` | root |
| **OLX HTTP transport** | `browser_transport.py` | src/core/ |
| **Kimovil specs** | `kimovil_scraper.py` | src/enrichment/ |
| **Entry point** | `main.py` | root |
| **Async scraping** | `async_scraper.py` | src/core/ |
| **Brand detection** | `patterns.py` | src/detection/ |
| **Re-categorization** | `recategorize.py` | src/detection/ |
| **Scoring algorithm** | `scoring.py` | src/analysis/ |
| **Market prices** | `market_data.py` | src/analysis/ |
| **Value analysis** | `analyzer.py` | src/analysis/ |
| **Gemini AI** | `gemini.py` | src/ai/ |
| **Cloud LLMs** | `cloud_llm.py` | src/ai/ |
| **Async details fetcher** | `listing_fetcher.py` | src/fetchers/ |
| **Configuration** | `config.py` | src/core/ |
| **Logging** | `logging.py` | src/infrastructure/ |
| **Results** | `data/sessions/{session}/results/` | data/ |
| **Reports** | `data/sessions/{session}/reports/` | data/ |
| **Logs** | `data/sessions/{session}/logs/` | data/ |

---

## Known Limitations

- Market prices manually maintained (102 models)
- Kimovil sits behind Cloudflare: headless Chromium always gets 403 `cf-mitigated: challenge`,
  curl_cffi's Chrome fingerprint gets the page. An IP flagged by request bursts
  gets 429 for every client; only cached specs are used until that block clears
- Russian/Kazakh language only
- OLX.kz specific (any OLX.kz region via `--location`, not other marketplaces)
- Rate limited to respect OLX servers
- OLX access depends on curl_cffi's browser TLS impersonation; if 403s return,
  check `IMPERSONATE` in `src/core/browser_transport.py` first

---

## Future Roadmap

- [ ] Real-time market prices instead of the hand-maintained table
- [x] Automated daily runs with alerts (`--notify` + a systemd timer or cron, see README)

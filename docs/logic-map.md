# Logic map

How an OLX.kz search (a price range in one city) becomes a ranked list of used phones, a TXT report and an optional Telegram alert.
The map describes the code as it is today, step by step.
Each step says what it decides, where the flow branches, and which module does it.

Read `CLAUDE.md` first for the commands and the layout.
Known gaps and fixes in progress are in `docs/plans/2026-11-05-logic-map-fixes.md`.

Rule: if you change a step or a branch, update this file in the same commit.
`tests/test_logic_map.py` checks that every `Module:` line points to a real module.

## The flow at a glance

```
CLI args → config overrides → session dir
  │
  ├─ 1  Scrape ............... which listing cards does OLX give for this price range
  ├─ 2  Recategorize ......... which brand and phone type is each title
  ├─ 3  Load ................. which phones go to analysis, with which cached details
  ├─ 4  Kimovil specs ........ which spec sheet belongs to each title
  ├─ 5  Score ................ how many points each phone gets, from title + specs + cached description
  ├─ 6  Details .............. which top phones get their listing page read, then re-score them
  ├─ 7  AI analysis .......... which top phones get a defect / bonus verdict
  ├─ 8  Save + report ........ what is written to disk
  └─ 9  Notify ............... which top listings are new since the last alert
  │
data/sessions/<session>/results + reports (+ Telegram)
```

Steps 1, 2 and 3-9 all run when no stage flag is given or with `--all`. Steps 3-8 are the `analyze` stage (`run_analyzer`), step 9 runs inside it.

## Where the flow splits by kind

There are two kinds of splits: phone brand/model (decided by regexes in three places) and phone type (decided once, by brand).

| Kind | Switched on by | Steps | What changes |
|---|---|---|---|
| Brand + type (iphone / android / unknown) | `BRAND_PATTERNS` regex over the title, best `score` wins | 1, 2, 3 | file the listing lands in; which file step 3 loads |
| Market model (price table key) | `extract_model_from_title` regex list, then partial match over table keys | 5 | discount, release year, tier; no match → brand points only |
| Kimovil model (brand, model) | `BRAND_ALIASES` + `MODEL_PATTERNS` | 4 | which spec page is fetched |
| Seller kind (private / shop) | `INCLUDE_BUSINESS`, OLX `is_business` from page state | 1, 5 | search param dropped; warning text only |
| City | `LOCATION` slug; listing `city` vs `HOME_CITY` | 1, 5 | URL; warning text only |

Three independent model parsers (`analysis/analyzer` for market + camera, `enrichment/spec_enrichment` with `detection/model_patterns` for Kimovil, `analysis/phone_normalizer` for the report title) can name one title differently. `detection/patterns.extract_model_info` is not called.

Examples:
- "Samsung S23 Ultra 256GB" → brand samsung/android; market key "samsung s23 ultra"; Kimovil ("Samsung", "Galaxy S23 Ultra").
- "Oppo Reno7 (обмен на iphone 13 pro)" → exchange wish stripped first; stays Oppo/android (all three parsers call `strip_exchange_wish`).
- "tecno spark 10 pro camera 50mp" → model "samsung a50"; "Oppo A52" → Samsung A52 price (finding #5).
- "Xiaomi Redmi Note 12 Pro" → market "redmi note 12 pro"; Kimovil ("Redmi", "Note 12 Pro").

Module: `detection/patterns`, `detection/model_patterns`, `analysis/analyzer`, `enrichment/spec_enrichment`

## Entry points

One entry point: `main.py` (`./run.sh` wraps `uv run main.py`). `analysis/analyzer.main`, `detection/recategorize.main` and `core/async_scraper.main` are standalone scripts with the same module code and no CLI.

| Flag | Effect | Notes |
|---|---|---|
| none or `--all` | steps 1, 2, 3-9 | `--all` is the same as no flag |
| `--scrape` / `--recategorize` / `--analyze` | only the named stages (can be combined) | a scrape that finds nothing does not stop the later stages |
| `--min-price --max-price --max-pages --days-back --location --include-business --phone-type` | written into `core/config` before anything runs | change the session name (except `--max-pages`, `--days-back`) |
| `--gemini` | builds `GeminiAnalyzer`, `--gemini-top-n` (30), `--gemini-photos` | Gemini is primary when no cloud LLM is on, else the fallback for cloud failures |
| `--cerebras` / `--openrouter` | cloud LLM, Cerebras wins over OpenRouter | no `--vercel` flag: `use_vercel` is never passed |
| `--notify` | step 9 | needs `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| `--show-config` | prints config, exits | |

Defaults (`core/config`): LOCATION "alma-ata", price 90000-380000 KZT, `PHONE_TYPE_FILTER` "android", private sellers only, `MAX_PAGES` 25 (per price slice), `TOP_RECOMMENDATIONS_COUNT` 50. No AI unless a flag asks.
Exit code: 0 when every stage that ran reported success, 1 otherwise, 2 on invalid config (`validate_config`).
Session name: `<location>_<min>k-<max>k_<phone type>[_shops]`; the same name reuses the same folder and its data.

Module: `../main`, `core/config`, `infrastructure/setup_env`, `infrastructure/logging`

## Steps

### 1. Scrape

Decides: which listing cards OLX returns for the price range, and which of them are new.
In: min/max price, city slug. Out: `listings` (dicts with title, price, link, status, brand, phone type, `is_business`, `city`).
Branches:
- first request per range reads OLX's result count from page state; count >= 1000 (OLX cap) and range wider than 1000 KZT → range split in half, recursively;
- count unreadable → range kept whole, `max_pages` pages fetched; a count of 0 pages is treated the same way (#16);
- `INCLUDE_BUSINESS` off → `search[private_business]=private` sent; on → dropped;
- each slice fetches `min(pages, MAX_PAGES)` pages at once through `PoliteClient` (paced, retried twice on 429/5xx, Chrome TLS fingerprint transport);
- card without a link → skipped; link already seen → skipped.
`--days-back` is only logged: nothing sends it to OLX or filters by date (#7).
Fails: a failed page is logged and skipped, the rest is kept. A failure in a count request (`_price_slices`) is not caught there and ends the step with `([], [], [])`. Zero listings → step returns empty, pipeline goes on.
Then `merge_with_existing`: loads `all_listings.json` of the session, adds only links not yet present. Old entries are never refreshed or removed (#3).
Then `save_results`: writes `all_listings.json`, `iphones.json`, `androids.json`, `unknown.json`. `PHONE_TYPE_FILTER` empties the other list in the result tuple and in its file (android → `iphones.json` written empty; step 2 refills it). Also writes `session_info.json`.
The step's success flag is true when any of the three lists is non-empty, so `--phone-type iphone` no longer reports FAILED (#6, fixed 2026-11-05).
Module: `core/async_scraper`, `core/browser_transport`, `core/config`

### 2. Recategorize

Decides: brand and phone type of every stored listing, again, with the current patterns.
In: `all_listings.json`. Out: the four JSON files rewritten.
Branches:
- brand by regex over the lowercased title, exchange wish stripped; highest `score` among matching brands wins; no match → "unknown";
- type is the brand's type (iphone / android).
Ignores `PHONE_TYPE_FILTER`: `iphones.json` and `androids.json` are both filled. Ignores `MIN_BRAND_CONFIDENCE` (#7).
Fails: missing file → warning, step returns empty (success flag False); any error → logged, empty.
Module: `detection/recategorize`, `detection/patterns`

### 3. Load phones for analysis

Decides: which file feeds the analyzer and which old details are reused.
In: `androids.json` / `iphones.json`. Out: list of phone dicts.
Branches:
- `PHONE_TYPE_FILTER` android → androids file; iphone → iphones file; both → both files;
- no session file exists → legacy `data/results/androids_all.json`; missing too → empty list, "No Android phones to analyze", stage FAILED;
- phone whose link is in `androids_analyzed.json` with `details_fetched` → cached description, photos, specs are merged under the fresh fields.
Includes every stored listing, also ones sold since (#4).
Module: `analysis/analyzer`

### 4. Kimovil specs

Decides: real specs (screen, RAM, storage, battery, chip) for each title.
In: all loaded phones. Out: `kimovil_specs` dict or None on each phone.
Branches:
- title not parsed to (brand, model) → None; brands without `MODEL_PATTERNS` (Oppo, Realme, Vivo, Honor, Huawei...) always None;
- brand = first `BRAND_ALIASES` hit in dict order: poco and redmi are checked before xiaomi, so "Xiaomi Redmi Note 12 Pro" → ("Redmi", "Note 12 Pro");
- model already cached with `success=1` in `data/cache/kimovil_specs.db` → cached specs;
- else one scrape per model per run (duplicates share one task), at most `KIMOVIL_MAX_CONCURRENT` (2) at a time, `KIMOVIL_REQUEST_DELAY` (2.5 s) apart;
- page needs more than 3 non-None fields → cached as success; else cached as failure (retried next run) and the partial dict still goes on the phone.
Fails: Cloudflare 403/429 or network error → None for that model, run goes on with title-only scoring. Scraper init error → enrichment skipped for the whole run.
Module: `enrichment/spec_enrichment`, `enrichment/kimovil_scraper`, `detection/model_patterns`

### 5. Score

Decides: `value_score` and the factor list of each phone, then the sort order.
In: phone + specs + description (cached from an earlier run; step 6 re-scores the top after a fetch). Out: `value_score`, `value_factors`, `warnings`, `discount_percent`, `normalized_title`.
Branches:
- market table hit → discount, age, tier points; discount above the plausible maximum for the model's age → minus 80 and a 🚩 factor;
- no market hit → brand points only, `discount_percent` None;
- storage, RAM, chip, display: specs first, title as fallback;
- condition, battery health, warranty: read title + description; a fresh phone has none on the first pass, step 6 re-scores it;
- camera: DXOMark table by extracted model (exact, then substring either way), tier default otherwise; no extracted model → tier default, no DXOMark;
- price-range points; score floored at 0;
- `is_business` → 🏪 warning; `city` != `HOME_CITY` → 📍 warning; warnings never change the score.
Exchange wish stripped for market, storage, RAM, camera, battery; condition, chip, display and warranty read the full title (#14).
Output is sorted by score descending.
Module: `analysis/analyzer`, `analysis/scoring`, `analysis/market_data`, `analysis/phone_normalizer`

### 6. Details

Decides: which phones get their listing page read for description, photos, views.
In: sorted phones, `top_count = min(len, TOP_RECOMMENDATIONS_COUNT)`. Out: same list with details on the top.
Branches:
- phone with `details_fetched` and a non-empty description → skipped (cached), so a listing removed after its first fetch is never re-checked (#4);
- others in the top → fetched all at once with plain `httpx` over the Chrome transport, no pacing, no retry;
- 404 / 410 / 403 → `is_unavailable` set, details empty; nothing reads that flag later (#4);
- other error → `fetch_error` set, details empty.
Then the top `top_count` phones are re-scored (step 5 rules, now with the description) and the whole list re-sorted; a phone that drops out of the top can be replaced by one without fetched details.
Module: `fetchers/listing_fetcher`, `fetchers/listing_parser`, `core/browser_transport`

### 7. AI analysis

Decides: defect and bonus verdict for the top phones; adds or subtracts points.
In: sorted phones. Out: `<provider>_analysis`, changed `value_score`, re-sort.
Branches:
- no cloud LLM and no Gemini enabled (flag missing or API key missing) → step skipped;
- cloud LLM enabled (Cerebras > OpenRouter) → analyses the first `min(gemini_top_n or top_count, top_count)` phones; `gemini_top_n` is set only with `--gemini`, so `--cerebras` alone analyses 50;
- cloud failures → Gemini analyses those phones if Gemini is enabled; otherwise a warning;
- Gemini enabled and no cloud LLM → Gemini analyses the first `min(gemini_top_n or top_count, top_count)` phones as primary;
- verdict: bonus points added; suspicious −30; critical and unusable −60; major −25 (score floored at 0).
Results are cached per session in `<provider>_cache/responses.json` (Gemini: `gemini_cache/`), key = MD5 of title + price: same title + price share a verdict, a new description reuses the old one (#9).
Fails: a phone whose analysis fails keeps its score; error is only counted.
Module: `analysis/analyzer`, `ai/cloud_llm`, `ai/gemini`, `infrastructure/cache`

### 8. Save + report

Decides: what lands on disk.
Writes `androids_analyzed.json` (all phones), `TOP_<N>_ANDROID.json`, `reports/TOP_RECOMMENDATIONS_<timestamp>.txt` (top N, with warnings, factors, description cut to 500 chars). `MIN_VALUE_SCORE` is not applied (#7).
The report prints only a Gemini verdict; a Cerebras/OpenRouter verdict (issues, recommendation) is in the JSON only (#15).
Console shows the top 5. No analyzed phones → stage returns False, nothing written.
Module: `analysis/analyzer`, `core/config`

### 9. Notify

Decides: which top listings are new since the last alert.
In: top phones, `--notify`. Out: Telegram messages.
Branches:
- token or chat id missing → warning, nothing sent;
- top `ALERT_TOP_N` (10) whose link is not in `<session>/alerts_sent.json` → sent, packed under the Telegram size limit;
- first failed send → stop; links of unsent messages stay unrecorded and go out next run.
Fails: any error is logged and never fails the stage.
Module: `infrastructure/alerts`

## Side flows

### Standalone scripts

`detection/recategorize.main`, `analysis/analyzer.main`, `core/async_scraper.main` repeat steps 2, 3-8 and 1 without `main.py`. They read the same config and session.
Module: `detection/recategorize`, `analysis/analyzer`, `core/async_scraper`

### Logging

`infrastructure/logging.configure_logging` is called after CLI overrides so the log folder carries the session name. Rotation and retention come from constants in that module, not from `LOG_*` in config (#7).
Module: `infrastructure/logging`

## Known gaps

- Merge keeps old prices and sold listings forever (#3).
- Removed or forbidden listings stay in the ranking and alerts (#4).
- `[aа]\s*(\d+)` runs before every non-Samsung pattern: "Oppo A52" gets the Samsung A52 price, "camera 50mp" becomes "samsung a50" (#5).
- `--days-back`, `MIN_VALUE_SCORE`, `REQUIRE_MARKET_DATA`, `MIN_BRAND_CONFIDENCE`, `LOG_*` config do nothing (#7).
- AI verdict cache keyed on title + price: equal listings share a verdict, new descriptions are not re-read (#9).
- Condition, chip, display, warranty read the exchange-wish part of the title (#14).
- Cloud LLM verdict text never reaches the report (#15).

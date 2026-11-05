# Plan: logic map findings

Findings from writing `docs/logic-map.md` on 2026-11-05. Independent review done the same day: #4, #5, #9 widened, #12-#16 added.
The map describes the code as it is; this file says what is wrong with it and what we propose. New findings are appended.
A fixed finding gets ✅ and the map is updated in the same commit.

Severity: HIGH: wrong result for the user. MEDIUM: worse result than it could be. LOW: noise, debt, docs.
"Question": not sure if bug or intent; the owner decides. "Not confirmed": needs a live run.

## Findings

| # | Map step | What is wrong | We propose | Severity |
|---|---|---|---|---|
| ✅ 1 | 7, Entry points | `_run_ai_analysis_pipeline` (`src/analysis/analyzer.py:841`) runs only the cloud LLM and then Gemini for its failures. `_run_gemini_analysis` (`:665`) is never called from the pipeline. `./run.sh --gemini` (also `--gemini-photos`, `--gemini-top-n`) analyses nothing. | Call `_run_gemini_analysis` as primary when no cloud LLM is enabled. | HIGH, fixed 2026-11-05 |
| ✅ 2 | 5, 6 | Scoring (`analyzer.py:~955`) runs before details are fetched (`:959`), and scores are not recomputed after. Condition, battery and warranty rules read the description, so on a first run they see only the title. A phone with a cached description from an earlier run scores differently from a fresh one. | Re-score the top N after step 6 (or fetch before scoring). | HIGH, fixed 2026-11-05 |
| 3 | 1 | `merge_with_existing` (`src/core/async_scraper.py:410`) adds only unseen links. A changed price or title of a known link is dropped, a delisted link stays forever. `androids.json` then carries stale prices into scoring. | Refresh known links with the new scrape; decide how to age out missing ones. | MEDIUM |
| 4 | 3, 6 | `is_unavailable` (404/410/403, `src/fetchers/listing_fetcher.py:~305`) is set but nothing downstream reads it. Removed listings stay in the ranking, the report and the Telegram alert. A listing fetched once with a description is skipped as cached on every later run (`listing_fetcher.py:193`), so its removal is never seen. | Drop or flag unavailable phones before save and notify. | MEDIUM |
| 5 | Split table, 5 | `extract_model_from_title` has `r"[aа]\s*(\d+)"` with no `\b` and no brand check (`analyzer.py:224`), and it runs before the Xiaomi, Redmi, Poco, Pixel, OnePlus, Huawei patterns. Checked: "Oppo A52 4/64" → "samsung a52" → Samsung A52 price (216938, 2021) and its discount; "tecno spark 10 pro camera 50mp" → "samsung a50", "Redmi 9A 2/32" → "samsung a2", "Huawei nova 11i" → "samsung a11" (no table key, so market falls back to the partial match; camera gets the wrong model). | Apply the pattern only when the title is Samsung (brand detected), plus `\b`; `\b` alone does not fix "Oppo A52". | MEDIUM |
| 6 | 1, Entry points | `results["scrape"] = len(androids) > 0` (`main.py:332`) uses the phone-type-filtered list. With `--phone-type iphone` the list is empty, so the stage shows FAILED and the process exits 1. | Judge success on the unfiltered count. ✅ 2026-11-05 fixed (`bool(iphones or androids or unknown)`, `tests/test_pipeline_phone_type.py`); option kept, not removed. | MEDIUM |
| 7 | Entry points, 1, 2, 8 | Config nothing reads: `DAYS_BACK` (only logged and written to session info; `--days-back` is advertised), `MIN_VALUE_SCORE`, `REQUIRE_MARKET_DATA`, `MIN_BRAND_CONFIDENCE` (validated only), `LOG_LEVEL`, `MAX_LOG_FILE_SIZE`, `MAX_LOG_BACKUPS`, `LOG_RETENTION_DAYS` (`logging.py` uses its own `DEFAULT_*`). `CLAUDE.md` lists them as active. | Wire them in or delete them and the flag. | MEDIUM |
| 8 | 7 | `gemini_top_n` is `max_ai_analysis if use_gemini else None` (`main.py:236`), so `--cerebras` alone analyses all 50 and ignores the 30 default of `--gemini-top-n`. | Question: pass the value whenever AI is on. | LOW |
| 9 | 7 | `CustomCache.generate_phone_cache_key` reads `url` (`src/infrastructure/cache.py:97`); phones carry `link`. The key is always MD5(title + price) (`:101-104`), so two listings with the same title and price ("Redmi Note 12 8/256", 70000) share one verdict, and a verdict made with an empty description (fetch failed) is reused after the description appears. | Key on `link` + a hash of the description. | MEDIUM (was LOW: common titles at round prices collide) |
| 10 | 6 | Details fetch sends up to 50 requests at once with no pacing or retry, unlike the search (`PoliteClient`). A 403 burst is recorded as "forbidden" (#4). | Question: reuse `PoliteClient`. | LOW |
| 11 | docs | Stale text: log "ready (Tier 2 fallback)" for the cloud LLM that is Tier 1 (`analyzer.py:193`); `enrich_phones_batch(max_concurrent)` is unused, the limit lives in the scraper semaphore; `main.py` docstring names `--scrape-only` / `--analyze-only`, which do not exist; `kimovil_scraper.py:348` comment says failures are cached to avoid re-scraping, but `_get_cached_specs` reads only `success=1`. | Fix text. | LOW |
| ✅ 12 | 5 | `get_camera_score` and `get_dxomark_score` partial match `model_lower in camera_model` (`src/analysis/scoring.py:1240`, `:1268`); with no extracted model `model_lower` is "", which is in every key, so the first entry (Huawei P60 Pro) wins. Checked: "Infinix Hot 30 8/128" gets camera +30 "📸 Top camera" and the report prints "DXOMark 156"; "Xiaomi 13" gets 13. Every Tecno, Infinix, Realme, Vivo, Honor, Motorola title the market extractor does not know gets the maximum camera score. | Return the tier default / 0 when the model is empty; require the key to start the model, not the reverse. | HIGH, fixed 2026-11-05 |
| ✅ 13 | 4, split table | `SpecEnricher.extract_brand_and_model` takes the first `BRAND_ALIASES` hit in dict order (`src/enrichment/spec_enrichment.py:79`, `src/detection/model_patterns.py:5`): xiaomi before redmi and poco. Checked: "Xiaomi Redmi Note 12 Pro 8/256" → ("Xiaomi", "12 Pro"), "Xiaomi Poco X5 Pro" → ("Xiaomi", "5 Pro"), "Xiaomi Redmi 12C" → ("Xiaomi", "12"). Storage, RAM, chip and display score from specs first, so a mid-range phone can get flagship chip and display points. Not confirmed: which page Kimovil serves for these URLs (no live run). | Check sub-brands (redmi, poco) before xiaomi, or reuse `detected_brand`. | HIGH, fixed 2026-11-05 |
| 14 | 5 | Condition, processor, display and warranty get `phone["title"]` (`analyzer.py:443`, `:462`, `:485`, `:494`), the title before `strip_exchange_wish`. Checked: "Poco X5 обмен на iphone в идеальном состоянии" scores +15 "✨ Excellent condition" from the wished-for phone; stripped title scores 0. | Pass `sold_title` to all title readers. | MEDIUM |
| 15 | 7, 8 | `_write_phone_entry` prints only `gemini_analysis` (`analyzer.py:1076`); `<provider>_analysis` from Cerebras/OpenRouter (issues, recommendation) and its penalty/bonus are not in the report or in `value_factors`. With `--cerebras` a phone moves by −25/−60/+N with no reason shown. | Print the cloud verdict too and add its penalty/bonus to the factors. | MEDIUM |
| 16 | 1 | `slice_pages = min(pages, max_pages_val) if pages else max_pages_val` (`src/core/async_scraper.py:271`): a slice with a readable count of 0 pages (no results) is fetched as if unreadable, 25 empty pages. | Use the unreadable branch only when `totals is None`. | LOW |

## Fixed

- #1: `_run_ai_analysis_pipeline` runs `_run_gemini_analysis` as primary when no cloud LLM is enabled; with a cloud LLM, Gemini stays the fallback.
- #2: `analyze_all_androids` re-scores the top N after the details fetch and re-sorts the whole list.
- #12: `get_camera_score` / `get_dxomark_score` skip the table for an empty model (tier default, DXOMark None). The reverse substring match is kept ("pixel 8 pro" still finds "google pixel 8 pro").
- #13: `BRAND_ALIASES` lists poco and redmi before xiaomi, so "Xiaomi Redmi Note 12 Pro" → ("Redmi", "Note 12 Pro"), the same Kimovil URL a plain "Redmi Note 12 Pro" title already used.

## Order of work

1. #1, #2 (both in `analyzer.py`, shared tests in `tests/test_analyzer_workflows.py`).
2. #3, #4 (stale data: scraper merge, details flag, notify).
3. #5, #6, #7.
4. #8-#11.
5. #12, #13 (HIGH, scoring inputs), then #14, #15, #16.

## Done when

- [ ] every finding has ✅ or a "keep as is" decision with a reason;
- [ ] Known gaps in the map lists every open HIGH and MEDIUM finding.

## Live-run set (proposed, not run)

| Input | Branch it should take (step) | Look at |
|---|---|---|
| `--analyze --gemini` with `GEMINI_API_KEY` | 7: Gemini as primary | log shows Gemini analysing (finding #1) |
| `--analyze --cerebras` twice on one session | 5/6: second run has cached descriptions | top 10 order differs between runs (#2) |
| `--scrape` twice a day apart | 1: merge | price of a known link updated (#3) |
| a listing deleted on OLX, then `--analyze` | 6: 404 | still in report (#4) |
| title "tecno spark 10 pro camera 50mp 128gb" via `extract_model_from_title` | split table | model key (#5) |
| `--phone-type iphone --scrape` | 1 | stage status and exit code (#6) |
| `--min-price 15000 --max-price 80000 --phone-type both` | 1: slice split, 3: both files | slice log lines, count in report |
| `--notify` with and without token | 9 | warning vs messages; `alerts_sent.json` |
| `--location alm --include-business` | 1, 5 | 🏪 and 📍 warnings |
| "Infinix Hot 30 8/128" through `calculate_value_score` | 5: camera | `camera_score` 30 (#12) |
| "Xiaomi Redmi Note 12 Pro 8/256" through `--analyze` | 4: Kimovil | URL and `processor_chipset` in `kimovil_specs` (#13) |
| `--analyze --cerebras` | 7, 8 | cloud verdict in the TXT report (#15) |

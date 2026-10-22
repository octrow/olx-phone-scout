<p align="center">
  <img src="assets/readme/hero.svg" width="100%" alt="olx-phone-scout: finds the best-value used phones on OLX.kz. Shown next to the title: the top entry of a real report, an iPhone 11 Pro Max 256GB for 80,000 KZT with its value factors">
</p>

<p align="center">
  <a href="https://github.com/octrow/olx-phone-scout/actions/workflows/ci.yml"><img src="https://github.com/octrow/olx-phone-scout/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/octrow/olx-phone-scout"><img src="https://api.scorecard.dev/projects/github.com/octrow/olx-phone-scout/badge" alt="OpenSSF Scorecard"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.12%2B-blue.svg" alt="Python 3.12+">
  <br>
  <b>English</b> · <a href="README.ru.md">Русский</a>
</p>

A command-line tool for anyone buying a used phone on OLX.kz. It reads every listing in your price
range, works out the brand and model from messy titles, adds specs from Kimovil, compares the asking
price with the model's market price and writes a ranked report. Built for Almaty, works for any OLX.kz region.

<p align="center">
  <img src="assets/readme/demo.gif" width="100%" alt="A real run of ./run.sh --min-price 150000 --max-price 160000: 396 listings scraped in about 3 seconds, 117 Android phones scored, top 5 printed with their discounts from market price (played at 2.5x speed)">
</p>

## A real run

The top of the report from `./run.sh --min-price 15000 --max-price 80000 --phone-type both --location alm`
(6,557 listings analyzed), trimmed:

```
📱 iPhone 11 Pro Max (iPhone 11 Pro Max 256GB Gold)
💰 PRICE: 80,000 KZT
📅 RELEASE YEAR: 2019
📍 LOCATION: Гульдала - 27 сентября 2026 г.
⚠️  📍 OUTSIDE АЛМАТЫ: Гульдала, you'll need to travel

⭐ VALUE FACTORS:
   ⭐⭐⭐ Ultra Flagship
   💾 Good 256GB storage
   ✨ Excellent condition
   🔋 Excellent battery (95%+)
```

## What it does

- **Reads the whole price range.** OLX returns at most 1000 results per search, so the range is split
  into price slices until each one fits under that cap. All pages are fetched concurrently, paced and
  retried.
- **Understands messy titles.** 22 brands, Cyrillic spellings and common typos ("xioami", "techno",
  "poko", "z фолд"). Phones offered *in exchange* ("обмен на iphone 13") don't count as the phone for sale.
- **Adds specs from Kimovil.** Screen, chipset, AnTuTu, battery, charging and DxOMark, cached in SQLite
  across runs.
- **Scores value.** Discount from the market price (102 models), release year, tier, storage, RAM,
  camera and condition. Implausible discounts are capped, out-of-town listings and shops are flagged.
- **Optional AI pass.** Gemini, Cerebras or OpenRouter read the description (and optionally the photos)
  for defects and extras. No API key needed for the rest of the pipeline.

## How it differs

- **OLX's own search** filters by price and sorts by date or price. It doesn't know what a model is
  worth, so a cheap old phone and a well-priced recent flagship look alike, and "xioami 14 512/16" is
  just a title.
- **Price comparison sites** cover new phones in shops, not private used listings.
- **Generic scrapers** give you raw listings. Brand detection, specs, scoring and getting past OLX's
  TLS fingerprint check are left to you.

## How it works

<p align="center">
  <img src="assets/readme/pipeline.svg" width="100%" alt="Pipeline: scrape every listing in price slices, detect brand and model, then score value with Kimovil specs and market prices into the top 50 report">
</p>

OLX and Kimovil both sit behind bot protection that checks the TLS fingerprint, not just headers.
Requests go through [curl_cffi](https://github.com/lexiforest/curl_cffi) impersonating Chrome, with
pacing and retries from [market-sources](https://github.com/octrow/market-sources). Kimovil pages are
parsed with selectolax; no browser is involved.

Architecture notes for contributors and coding agents are in [CLAUDE.md](CLAUDE.md).

## Install

Needs Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/octrow/olx-phone-scout.git
cd olx-phone-scout
uv sync
```

For the AI pass, copy `.env.example` to `.env` and fill in the key of the provider you use.

## Run

```bash
./run.sh                    # full pipeline: scrape → recategorize → analyze
./run.sh --scrape           # scrape OLX only
./run.sh --recategorize     # re-run brand detection on saved listings
./run.sh --analyze          # analyze saved listings only
./run.sh --show-config      # print the configuration and exit
```

`./run.sh` is a thin wrapper around `uv run main.py`; the same flags work with either.

```bash
./run.sh --min-price 150000 --max-price 300000 --max-pages 10 --days-back 14
./run.sh --min-price 15000 --max-price 80000 --phone-type both   # Android + iPhone
./run.sh --location alm --include-business   # Almaty city + region, shops too (marked 📍 / 🏪)
./run.sh --gemini           # Gemini AI analysis (--gemini-photos, --gemini-top-n N)
./run.sh --cerebras         # or --openrouter
```

`--location` takes any OLX.kz region slug (`astana`, `shymkent`, `karaganda`, ...); see `--help`.

## Daily runs

`--notify` sends the listings that entered the top 10 since the last notification to a Telegram chat:
title, price, score and link. Set `TELEGRAM_BOT_TOKEN` (from [@BotFather](https://t.me/BotFather))
and `TELEGRAM_CHAT_ID` in `.env`. Sent links are remembered per session in `alerts_sent.json`, so
each run reports only what is new. A missing token or a failed send is a warning, never a failed
run; unsent listings are retried next time. The first run sends the whole current top 10.

There is no built-in scheduler. A systemd user timer, `~/.config/systemd/user/olx-phone-scout.service`:

```ini
[Service]
Type=oneshot
ExecStart=/path/to/olx-phone-scout/run.sh --notify
```

and `~/.config/systemd/user/olx-phone-scout.timer`:

```ini
[Timer]
OnCalendar=*-*-* 09:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable it with `systemctl --user enable --now olx-phone-scout.timer` (`Persistent=true` catches up
after sleep). Or with cron (`uv` must be on cron's `PATH`):

```cron
0 9 * * * /path/to/olx-phone-scout/run.sh --notify >/dev/null 2>&1
```

## Output

Each run writes to a session folder named after its settings, e.g.
`data/sessions/alma-ata_90k-380k_android/`:

- `results/`: `all_listings.json`, `androids.json`, `iphones.json`, `unknown.json`,
  `androids_analyzed.json`, `TOP_50_ANDROID.json`
- `reports/TOP_RECOMMENDATIONS_{timestamp}.txt`: the ranked, human-readable report
- `logs/`: one log per pipeline step

Kimovil specs are cached for all sessions in `data/cache/kimovil_specs.db`.

## Configuration

Defaults live in `src/core/config.py`; CLI flags override them.

| Setting | Default |
|---------|---------|
| `LOCATION` | `alma-ata` |
| `MIN_PRICE` / `MAX_PRICE` | 90,000 / 380,000 KZT |
| `MAX_PAGES` | 25 per price slice (OLX's maximum) |
| `DAYS_BACK` | 25 |
| `PHONE_TYPE_FILTER` | `android` (`--phone-type android\|iphone\|both`) |
| `REQUEST_DELAY` | 1.5 s between OLX requests |

Kimovil pacing is in `src/core/constants.py`: `KIMOVIL_MAX_CONCURRENT = 2`,
`KIMOVIL_REQUEST_DELAY = 2.5` s. Each model is fetched at most once per run.

## Troubleshooting

- **OLX returns 403 on every page.** CloudFront blocks by TLS fingerprint. Try another `IMPERSONATE`
  target in `src/core/browser_transport.py`, or update `curl_cffi`.
- **Kimovil answers 429 for most phones.** That is a Cloudflare block on your IP after a burst of
  requests, not a normal rate limit. Wait a few hours and run `./run.sh --analyze` again; found specs
  are cached, so each run fills in more.

## Limitations

- Market prices are maintained by hand (`src/analysis/market_data.py`, 102 models).
- OLX.kz only; listing text is expected in Russian or Kazakh.

## Development

```bash
uv run pytest               # tests (+ coverage report in htmlcov/)
uv run ruff check . && uv run ruff format --check .
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)

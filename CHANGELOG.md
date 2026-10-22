# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `--notify`: after the analysis, listings that entered the top 10 since the last notification are
  sent to a Telegram chat (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`). Sent links are remembered per
  session; a failed send never fails the run. README explains scheduling with a systemd timer or cron.
- Dependency: `tg-toolkit` (Bot API push; pulls in `telethon`).

## [1.0.4] - 2026-10-15

### Added
- Published on PyPI (`uvx olx-phone-scout`) via trusted publishing.
- Russian mirror of the code of conduct.

## [1.0.3] - 2026-10-15

### Changed
- openai SDK 2.53 → 3.26 (used by the Cerebras/OpenRouter/Vercel pass). 3.x switched to HTTPX2 and
  stopped installing httpx; the scraper keeps httpx as a direct dependency, so nothing else changes.
- Minor and patch updates for 5 dependencies.

## [1.0.2] - 2026-10-15

### Security
- urllib3 (a transitive dependency) bumped from 2.7.0 to 2.8.0: fixes two high and one moderate
  advisory in chunked response handling and HTTPS proxy TLS configuration.

## [1.0.1] - 2026-10-15

### Fixed
- The console no longer prints a line for every HTTP request, page and listing: library logs below
  WARNING go to the log files only, and progress bars stay intact.
- File paths in the console output are shown relative to the repo, not as absolute paths.

### Changed
- CI: actions pinned by commit SHA; gitleaks, zizmor and OpenSSF Scorecard added.
- README: demo GIF of a real run and a "How it differs" section.

## [1.0.0] - 2026-10-13

First public release.

### Added
- Async OLX.kz scraper with automatic price slicing past OLX's 1000-result cap.
- Brand and model detection for 22 brands, with Cyrillic spellings and common typos.
- Kimovil spec enrichment over curl_cffi + selectolax, cached in SQLite across runs.
- Value scoring against hand-maintained market prices for 102 models.
- Optional AI analysis via Gemini, Cerebras or OpenRouter.
- Any OLX.kz region (`--location`), shops (`--include-business`), Android and iPhone (`--phone-type`).
- Test suite: 454 tests covering the scraper, parser, brand detection, scoring and analyzer.

### Fixed
- The report showed the value score as "out of 100" (e.g. 190/100); it now shows raw points.

[1.0.3]: https://github.com/octrow/olx-phone-scout/releases/tag/v1.0.3
[1.0.2]: https://github.com/octrow/olx-phone-scout/releases/tag/v1.0.2
[1.0.1]: https://github.com/octrow/olx-phone-scout/releases/tag/v1.0.1
[1.0.0]: https://github.com/octrow/olx-phone-scout/releases/tag/v1.0.0

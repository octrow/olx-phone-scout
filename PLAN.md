# План: olx-almaty-phone-analyzer

Точка входа: что осталось сделать (баги, планы, идеи). Дата 2026-11-05. Закрытый пункт удаляется или получает ✅ со ссылкой на коммит.

## Баги

Находки logic-map ([план](docs/plans/2026-11-05-logic-map-fixes.md), номера `#N` оттуда). Исправлены: #1, #2, #6, #12, #13.

- [x] ✅ 2026-11-05 HIGH (не закоммичено; `src/infrastructure/atomic.py` `write_json_atomic`: temp-файл + replace, применён в scraper, analyzer, cache; тест `tests/test_atomic_write.py`): файлы состояния пишутся поверх (kill или полный диск обрезает `all_listings.json`, кэш; merge читает битый файл). Фикс: temp-файл + `os.replace` (`src/core/async_scraper.py:490`, `src/analysis/analyzer.py:1010,1026`, `src/infrastructure/cache.py:58`) — [system-design.md, Risks](docs/system-design.md)
- [ ] MEDIUM #3: `merge_with_existing` не обновляет цену/название известных ссылок, снятые не удаляются (`src/core/async_scraper.py:410`)
- [ ] MEDIUM #4: `is_unavailable` (404/410/403) никто не читает, снятые объявления остаются в рейтинге и алерте (`src/fetchers/listing_fetcher.py:~305`)
- [ ] MEDIUM #5: `extract_model_from_title` с `[aа]\s*(\d+)` без `\b` и проверки бренда: "Oppo A52" → "samsung a52" (`src/analysis/analyzer.py:224`)
- [x] ✅ 2026-11-05 MEDIUM #6: `--phone-type iphone` давал FAILED и exit 1 (`main.py:332`). Починено, а не удалено: успех scrape считается по всем трём спискам, тест `tests/test_pipeline_phone_type.py`
- [ ] MEDIUM #7: конфиг, который ничего не читает (`DAYS_BACK`, `MIN_VALUE_SCORE`, `REQUIRE_MARKET_DATA`, `MIN_BRAND_CONFIDENCE`, `LOG_*`): подключить или удалить
- [ ] MEDIUM #9: ключ кэша LLM = MD5(title+price), `url` вместо `link` (`src/infrastructure/cache.py:97`)
- [ ] MEDIUM #14: условие/процессор/экран/гарантия читают `title` до `strip_exchange_wish` (`src/analysis/analyzer.py:443`)
- [ ] MEDIUM #15: вердикт Cerebras/OpenRouter и его бонус/штраф не видны в отчёте (`src/analysis/analyzer.py:1076`)
- [ ] MEDIUM (риск): запрос количества слайса падает без перехвата и даёт пустой прогон (`src/core/async_scraper.py:235-252`) — [Risks](docs/system-design.md)
- [ ] MEDIUM (риск): top-50 деталей без пейсинга и ретраев, вероятная причина бана IP (`src/fetchers/listing_fetcher.py:82,264`) — см. также #10
- [ ] MEDIUM (риск): нет защиты от параллельных запусков на одной сессии, нужен lockfile — [Risks](docs/system-design.md)
- [ ] MEDIUM (риск): нет breaker для блокировок Kimovil/OLX (стоп после N подряд 429/403) — [Risks](docs/system-design.md)
- [ ] LOW: #8, #10, #11, #16 — шум и долг, список в [плане](docs/plans/2026-11-05-logic-map-fixes.md)
- [ ] Issue [#12](https://github.com/octrow/olx-phone-scout/issues/12): "Total after merge" логируется дважды за scrape

## Планы и фичи

- [ ] openspec `add-olx-market-median`: медиана цен по модели из истории объявлений — [tasks](openspec/changes/add-olx-market-median/tasks.md)
- [ ] openspec `add-daily-run-alerts`: `--notify` и `alerts.py` уже в коде, задачи в tasks.md не отмечены; сверить, закрыть и заархивировать — [tasks](openspec/changes/add-daily-run-alerts/tasks.md)
- [ ] Реальные рыночные цены вместо ручной таблицы — [CLAUDE.md, Future Roadmap](CLAUDE.md)
- [ ] Закрыть logic-map: у каждой находки ✅ или решение "оставить" с причиной; Known gaps в карте = открытые HIGH/MEDIUM — [Done when](docs/plans/2026-11-05-logic-map-fixes.md)
- [ ] Живые прогоны из набора "Live-run set" (предложены, не запускались) — [план](docs/plans/2026-11-05-logic-map-fixes.md)
- [ ] Issue [#11](https://github.com/octrow/olx-phone-scout/issues/11): цены для часто встречающихся моделей
- [ ] Issue [#13](https://github.com/octrow/olx-phone-scout/issues/13): тесты извлечения бренда/модели из названия
- [ ] Issues [#19](https://github.com/octrow/olx-phone-scout/issues/19), [#20](https://github.com/octrow/olx-phone-scout/issues/20), [#22](https://github.com/octrow/olx-phone-scout/issues/22), [#23](https://github.com/octrow/olx-phone-scout/issues/23): тесты для `ai/gemini.py`, `detection/recategorize.py`, `enrichment/spec_enrichment.py`, `fetchers/listing_fetcher.py` (#23 needs-human)

## Идеи

- [ ] SQLite вместо JSON, когда файл сессии >100 MB или два запуска пересеклись — [system-design.md, §8](docs/system-design.md)
- [ ] LOW (риск): неограниченный рост `all_listings.json` (7226 объявлений, ок до ~100 MB) — [Risks](docs/system-design.md)
- [ ] LOW (риск): нет бэкапа `alerts_sent.json` и кэшей, `data/` только на этом хосте — [Risks](docs/system-design.md)
- [ ] LOW (риск): нет машинных метрик прогона (время, страницы, число 403); одна строка/JSON на прогон — [Risks](docs/system-design.md)

## Подробные планы

- [docs/plans/2026-11-05-logic-map-fixes.md](docs/plans/2026-11-05-logic-map-fixes.md): находки logic-map, порядок работ
- [docs/logic-map.md](docs/logic-map.md): как поиск становится рейтингом
- [docs/system-design.md](docs/system-design.md): system design 2026-11-05: ступень, расчёт нагрузки, отказы, риски
- Сводка по всем репо: `~/dev/docs/system-design-report-2026-11-05.md`
- [openspec/changes/](openspec/changes/): незаархивированные изменения
- [docs/daily-runs.md](docs/daily-runs.md): ежедневные запуски
- [docs/skills-roadmap-2026-11-05.md](docs/skills-roadmap-2026-11-05.md): навыки с рынка вакансий, 2 пункта: история цен в SQLite с медианой на SQL; ML-регрессия цены поверх неё

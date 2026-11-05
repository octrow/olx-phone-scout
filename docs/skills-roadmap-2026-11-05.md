# Навыки с рынка: что добавить (2026-11-05)

Источник: `~/dev/jobs/data/corpus_roadmap.md` (11.5k вакансий, 2026-11-05) против [system-design](system-design.md) и [logic-map](logic-map.md). Берём только то, что нужно самому проекту; чего проект не требует — в «Отвергнуто». Сводка по всем репо: `~/dev/docs/skills-roadmap-report-2026-11-05.md`.

## Предложения

- [ ] **[sql, sqlite]** История цен в SQLite (`listing_price` по model/storage/date) с медианой по окну на SQL — ровно то, что нужно openspec `add-olx-market-median`; SQLite уже есть (`kimovil_specs.db`). Усилие M.
- [ ] **[ml, scikit-learn, pandas]** Модель ожидаемой цены б/у (GradientBoosting / квантильная регрессия по модели, памяти, состоянию, возрасту) вместо ручной таблицы на 102 модели; baseline — медиана. Без накопленной истории не делать. Усилие L.

## Порядок

4 HIGH (Gemini, скоринг до деталей, пустая модель → «Top camera», порядок BRAND_ALIASES) + #5 (`extract_model_from_title`), #3/#4 → история цен → ML.

## Отвергнуто

- PostgreSQL: один писатель, следующая ступень — SQLite (§8).
- OTel/Prometheus: хватит одной JSON-строки метрик на прогон (в «Идеях»).
- Docker для cron на OCI: есть run.sh + systemd. MCP над TOP_50: проекту не нужно.

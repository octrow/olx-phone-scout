<p align="center">
  <img src="assets/readme/hero.ru.svg" width="100%" alt="olx-phone-scout находит самые выгодные б/у телефоны на OLX.kz. Рядом с названием первая запись реального отчёта: iPhone 11 Pro Max 256GB за 80 000 ₸ и его плюсы">
</p>

<p align="center">
  <a href="https://github.com/octrow/olx-phone-scout/actions/workflows/ci.yml"><img src="https://github.com/octrow/olx-phone-scout/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/octrow/olx-phone-scout"><img src="https://api.scorecard.dev/projects/github.com/octrow/olx-phone-scout/badge" alt="OpenSSF Scorecard"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.12%2B-blue.svg" alt="Python 3.12+">
  <br>
  <a href="README.md">English</a> · <b>Русский</b>
</p>

Находит хорошие б/у телефоны на OLX.kz и ранжирует их по выгоде.

Читает все объявления в вашем ценовом диапазоне и определяет бренд и модель по неаккуратным заголовкам.
Добавляет характеристики с Kimovil и сравнивает цену с рыночной ценой модели.
На выходе отчёт с рейтингом. Сделана для Алматы, работает с любым регионом OLX.kz.

Быстрый старт: `uv sync`, затем `./run.sh --min-price 150000 --max-price 300000` ([Установка](#установка)).

<p align="center">
  <img src="assets/readme/demo.gif" width="100%" alt="Реальный прогон ./run.sh --min-price 150000 --max-price 160000: 396 объявлений собрано примерно за 3 секунды, оценено 117 Android-телефонов, выведен топ-5 со скидкой от рыночной цены (ускорено в 2,5 раза)">
</p>

## Пример реального прогона

Начало отчёта после `./run.sh --min-price 15000 --max-price 80000 --phone-type both --location alm`
(проанализировано 6557 объявлений), с сокращениями:

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

## Что умеет

- Проходит весь ценовой диапазон. OLX отдаёт не больше 1000 результатов на поиск, поэтому диапазон
  режется на ценовые срезы, каждый из которых укладывается в лимит. Страницы грузятся параллельно,
  с паузами и повторами.
- Читает неаккуратные заголовки. 22 бренда, кириллица и опечатки («xioami», «techno», «poko»,
  «z фолд»). Телефон, который хотят получить *в обмен* («обмен на iphone 13»), не считается продаваемым.
- Добавляет характеристики с Kimovil: экран, процессор, AnTuTu, аккумулятор, зарядка, DxOMark.
  Кэш в SQLite.
- Оценивает выгоду: скидка от рыночной цены (102 модели), год выпуска, класс, память, ОЗУ, камера и
  состояние. Неправдоподобные скидки ограничиваются. Пригороды и магазины помечаются.
- Необязательный AI-анализ. Gemini, Cerebras или OpenRouter читают описание (и по желанию фото)
  и ищут дефекты и бонусы. Остальному пайплайну API-ключи не нужны.

## Чем отличается

Сравнение с другими способами искать б/у телефон на OLX.kz:

- Поиск OLX фильтрует по цене и сортирует по дате или цене. Сколько стоит модель, он не знает.
  Дешёвый старый телефон и флагман прошлого года по хорошей цене выглядят одинаково, а «xioami 14 512/16»
  для него просто заголовок.
- Сайты сравнения цен показывают новые телефоны в магазинах, а не частные б/у объявления.
- Универсальные парсеры отдают сырые объявления. Определение бренда, характеристики, оценку и
  проверку TLS-отпечатка на OLX придётся делать самому.

## Как устроено

<p align="center">
  <img src="assets/readme/pipeline.ru.svg" width="100%" alt="Пайплайн: сбор всех объявлений по ценовым срезам, определение бренда и модели, оценка выгоды по Kimovil и рыночным ценам, отчёт с топ-50">
</p>

OLX и Kimovil закрыты защитой от ботов, которая проверяет TLS-отпечаток и заголовки.
Запросы идут через [curl_cffi](https://github.com/lexiforest/curl_cffi) с отпечатком Chrome, паузы и
повторы берутся из [market-sources](https://github.com/octrow/market-sources). Страницы Kimovil
разбираются selectolax. Браузер не нужен.

Заметки об архитектуре для контрибьюторов и coding-агентов в [CLAUDE.md](CLAUDE.md).

## Установка

Нужны Python 3.12+ и [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/octrow/olx-phone-scout.git
cd olx-phone-scout
uv sync
```

Для AI-анализа скопируйте `.env.example` в `.env` и впишите ключ нужного провайдера.

## Запуск

```bash
./run.sh                    # весь пайплайн: сбор → перекатегоризация → анализ
./run.sh --scrape           # только сбор с OLX
./run.sh --recategorize     # заново определить бренды у сохранённых объявлений
./run.sh --analyze          # только анализ сохранённых объявлений
./run.sh --show-config      # показать настройки и выйти
```

`./run.sh` - тонкая обёртка над `uv run main.py`, флаги у них одинаковые.

```bash
./run.sh --min-price 150000 --max-price 300000 --max-pages 10 --days-back 14
./run.sh --min-price 15000 --max-price 80000 --phone-type both   # Android + iPhone
./run.sh --location alm --include-business   # Алматы с областью, и магазины тоже (метки 📍 / 🏪)
./run.sh --gemini           # AI-анализ через Gemini (--gemini-photos, --gemini-top-n N)
./run.sh --cerebras         # или --openrouter
```

`--location` принимает слаг любого региона OLX.kz (`astana`, `shymkent`, `karaganda`, ...), список в `--help`.

## Ежедневный запуск

`--notify` отправляет в Telegram объявления, попавшие в топ-10 после прошлого запуска.
Задайте в `.env` `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID`.

Настройка планировщика (systemd, cron) и подробности: [docs/daily-runs.ru.md](docs/daily-runs.ru.md).

## Результаты

Каждый запуск пишет в папку сессии, названную по настройкам, например
`data/sessions/alma-ata_90k-380k_android/`:

- `results/`: `all_listings.json`, `androids.json`, `iphones.json`, `unknown.json`,
  `androids_analyzed.json`, `TOP_50_ANDROID.json`
- `reports/TOP_RECOMMENDATIONS_{timestamp}.txt`: отчёт с рейтингом для чтения
- `logs/`: по логу на каждый шаг

Характеристики Kimovil кэшируются для всех сессий в `data/cache/kimovil_specs.db`.

## Настройки

Значения по умолчанию лежат в `src/core/config.py`, флаги CLI их переопределяют.

| Параметр | По умолчанию |
|----------|--------------|
| `LOCATION` | `alma-ata` |
| `MIN_PRICE` / `MAX_PRICE` | 90 000 / 380 000 ₸ |
| `MAX_PAGES` | 25 на ценовой срез (максимум OLX) |
| `DAYS_BACK` | 25 |
| `PHONE_TYPE_FILTER` | `android` (`--phone-type android\|iphone\|both`) |
| `REQUEST_DELAY` | 1,5 с между запросами к OLX |

Темп запросов к Kimovil задан в `src/core/constants.py`: `KIMOVIL_MAX_CONCURRENT = 2`,
`KIMOVIL_REQUEST_DELAY = 2.5` с. Каждая модель запрашивается не больше одного раза за запуск.

## Если что-то не работает

- **OLX отвечает 403 на каждую страницу.** CloudFront блокирует по TLS-отпечатку. Попробуйте другую
  цель `IMPERSONATE` в `src/core/browser_transport.py` или обновите `curl_cffi`.
- **Kimovil отвечает 429 почти на все телефоны.** Это блокировка Cloudflare на ваш IP после всплеска
  запросов, а не обычный лимит. Подождите несколько часов и снова запустите `./run.sh --analyze`:
  найденные характеристики кэшируются, и каждый запуск добирает ещё.

## Ограничения

- Рыночные цены ведутся вручную (`src/analysis/market_data.py`, 102 модели).
- Только OLX.kz; текст объявлений ожидается на русском или казахском.

## Разработка

```bash
uv run pytest               # тесты (+ отчёт о покрытии в htmlcov/)
uv run ruff check . && uv run ruff format --check .
```

См. [CONTRIBUTING.ru.md](CONTRIBUTING.ru.md).

## Лицензия

[MIT](LICENSE)

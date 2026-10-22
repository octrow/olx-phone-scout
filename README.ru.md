<p align="center">
  <img src="assets/readme/hero.ru.svg" width="100%" alt="olx-phone-scout находит самые выгодные б/у телефоны на OLX.kz. Рядом с названием — первая запись реального отчёта: iPhone 11 Pro Max 256GB за 80 000 ₸ и его плюсы">
</p>

<p align="center">
  <a href="https://github.com/octrow/olx-phone-scout/actions/workflows/ci.yml"><img src="https://github.com/octrow/olx-phone-scout/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/octrow/olx-phone-scout"><img src="https://api.scorecard.dev/projects/github.com/octrow/olx-phone-scout/badge" alt="OpenSSF Scorecard"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/python-3.12%2B-blue.svg" alt="Python 3.12+">
  <br>
  <a href="README.md">English</a> · <b>Русский</b>
</p>

Консольная утилита для тех, кто покупает б/у телефон на OLX.kz. Она читает все объявления в вашем
ценовом диапазоне и разбирает бренд и модель по неаккуратным заголовкам. Затем добавляет характеристики
с Kimovil, сравнивает цену с рыночной ценой модели и пишет отчёт с рейтингом. Сделана для Алматы, но
работает с любым регионом OLX.kz.

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

- **Проходит весь ценовой диапазон.** OLX отдаёт не больше 1000 результатов на поиск, поэтому диапазон
  режется на ценовые срезы, пока каждый не уложится в этот лимит. Страницы загружаются параллельно,
  с паузами и повторами.
- **Понимает неаккуратные заголовки.** 22 бренда, кириллица и частые опечатки («xioami», «techno»,
  «poko», «z фолд»). Телефон, который хотят получить *в обмен* («обмен на iphone 13»), не считается
  продаваемым.
- **Добавляет характеристики с Kimovil.** Экран, процессор, AnTuTu, аккумулятор, зарядка и DxOMark.
  Кэшируются в SQLite между запусками.
- **Оценивает выгоду.** Скидка от рыночной цены (102 модели), год выпуска, класс, память, ОЗУ, камера
  и состояние. Неправдоподобные скидки ограничиваются, объявления из пригородов и от магазинов
  помечаются.
- **Необязательный AI-анализ.** Gemini, Cerebras или OpenRouter читают описание (и по желанию фото)
  и ищут дефекты и бонусы. Остальной пайплайн работает без API-ключей.

## Чем отличается

- **Поиск самого OLX** фильтрует по цене и сортирует по дате или цене. Он не знает, сколько стоит
  модель, поэтому дешёвый старый телефон и флагман прошлого года по хорошей цене выглядят одинаково,
  а «xioami 14 512/16» для него просто заголовок.
- **Сайты сравнения цен** показывают новые телефоны в магазинах, а не частные б/у объявления.
- **Универсальные парсеры** отдают сырые объявления. Определение бренда, характеристики, оценку и
  обход проверки TLS-отпечатка на OLX придётся делать самому.

## Как устроено

<p align="center">
  <img src="assets/readme/pipeline.ru.svg" width="100%" alt="Пайплайн: сбор всех объявлений по ценовым срезам, определение бренда и модели, оценка выгоды по Kimovil и рыночным ценам, отчёт с топ-50">
</p>

OLX и Kimovil закрыты защитой от ботов, которая смотрит на TLS-отпечаток, а не только на заголовки.
Запросы идут через [curl_cffi](https://github.com/lexiforest/curl_cffi) с отпечатком Chrome, паузы и
повторы берутся из [market-sources](https://github.com/octrow/market-sources). Страницы Kimovil
разбираются selectolax, браузер не нужен.

Заметки об архитектуре для контрибьюторов и coding-агентов — в [CLAUDE.md](CLAUDE.md).

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

`./run.sh` — тонкая обёртка над `uv run main.py`, флаги у них одинаковые.

```bash
./run.sh --min-price 150000 --max-price 300000 --max-pages 10 --days-back 14
./run.sh --min-price 15000 --max-price 80000 --phone-type both   # Android + iPhone
./run.sh --location alm --include-business   # Алматы с областью, и магазины тоже (метки 📍 / 🏪)
./run.sh --gemini           # AI-анализ через Gemini (--gemini-photos, --gemini-top-n N)
./run.sh --cerebras         # или --openrouter
```

`--location` принимает слаг любого региона OLX.kz (`astana`, `shymkent`, `karaganda`, ...), список в `--help`.

## Ежедневный запуск

`--notify` отправляет в Telegram объявления, попавшие в топ-10 после прошлого уведомления: название,
цену, баллы и ссылку. Задайте в `.env` `TELEGRAM_BOT_TOKEN` (от [@BotFather](https://t.me/BotFather))
и `TELEGRAM_CHAT_ID`. Отправленные ссылки запоминаются для каждой сессии в `alerts_sent.json`,
поэтому каждый запуск сообщает только новое. Нет токена или отправка не удалась — это предупреждение,
а не упавший запуск; неотправленные объявления уйдут в следующий раз. Первый запуск присылает весь
текущий топ-10.

Встроенного планировщика нет. Таймер systemd для пользователя,
`~/.config/systemd/user/olx-phone-scout.service`:

```ini
[Service]
Type=oneshot
ExecStart=/path/to/olx-phone-scout/run.sh --notify
```

и `~/.config/systemd/user/olx-phone-scout.timer`:

```ini
[Timer]
OnCalendar=*-*-* 09:00
Persistent=true

[Install]
WantedBy=timers.target
```

Включается командой `systemctl --user enable --now olx-phone-scout.timer` (`Persistent=true`
догоняет пропущенный запуск после сна). Или через cron (`uv` должен быть в `PATH` у cron):

```cron
0 9 * * * /path/to/olx-phone-scout/run.sh --notify >/dev/null 2>&1
```

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

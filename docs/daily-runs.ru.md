# Ежедневный запуск

[README](../README.ru.md)

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

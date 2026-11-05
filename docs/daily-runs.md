# Daily runs

[README](../README.md)

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

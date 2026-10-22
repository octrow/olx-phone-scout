"""Telegram alerts for listings that newly entered the top of the ranking (`--notify`).

The links already sent are kept per session in `<session>/alerts_sent.json`, so a scheduled
run only reports what is new. Sending goes through `tg_toolkit.bot_send`: plain text, never
raises, scrubs the token from its own log lines.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from tg_toolkit.push import MAX_TEXT, bot_send

from src.core.constants import ALERT_TOP_N
from src.infrastructure.logging import logger

STATE_FILE = "alerts_sent.json"
TOKEN_VAR = "TELEGRAM_BOT_TOKEN"
CHAT_VAR = "TELEGRAM_CHAT_ID"

Ranked = tuple[int, dict[str, Any]]  # (rank in the top, phone)


def load_sent(session_dir: Path) -> set[str]:
    """Links already sent for this session; a missing or unreadable file reads as none sent."""
    path = session_dir / STATE_FILE
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError) as e:
        logger.warning(f"⚠️  Can't read {path.name} ({e}); treating every listing as unsent")
        return set()


def save_sent(session_dir: Path, links: set[str]) -> None:
    """Write the sent links atomically (temp file + rename)."""
    path = session_dir / STATE_FILE
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(sorted(links), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def select_new(top_phones: list[dict[str, Any]], sent: set[str]) -> list[Ranked]:
    """Listings in the top `ALERT_TOP_N` whose link has not been sent yet, with their rank."""
    return [
        (rank, phone)
        for rank, phone in enumerate(top_phones[:ALERT_TOP_N], 1)
        if phone.get("link") and phone["link"] not in sent
    ]


def format_listing(rank: int, phone: dict[str, Any]) -> str:
    return (
        f"#{rank} · {phone.get('title', 'Unknown')}\n"
        f"{phone.get('price', 0):,} KZT · score {phone.get('value_score', 0):.1f}\n"
        f"{phone['link']}"
    )


def build_messages(header: str, phones: list[Ranked]) -> list[tuple[str, list[str]]]:
    """Pack listings into messages under Telegram's limit, never cutting one in two.

    Returns (text, links in that text) pairs, so links are recorded per accepted message.
    """
    messages: list[tuple[str, list[str]]] = []
    text, links = header, list[str]()
    for rank, phone in phones:
        block = format_listing(rank, phone)
        if links and len(text) + 2 + len(block) > MAX_TEXT:
            messages.append((text, links))
            text, links = "", []
        text = f"{text}\n\n{block}" if text else block
        links.append(phone["link"])
    if links:
        messages.append((text, links))
    return messages


def notify_new_top(top_phones: list[dict[str, Any]], session_dir: Path, session_name: str) -> int:
    """Send the new top listings to Telegram; returns how many were sent. Never raises on a
    missing config or a failed send: the unsent links stay unrecorded and are retried next run."""
    token, chat_id = os.getenv(TOKEN_VAR), os.getenv(CHAT_VAR)
    missing = [name for name, value in ((TOKEN_VAR, token), (CHAT_VAR, chat_id)) if not value]
    if missing:
        logger.warning(f"⚠️  --notify skipped: {', '.join(missing)} not set (see .env.example)")
        return 0

    sent = load_sent(session_dir)
    new = select_new(top_phones, sent)
    if not new:
        logger.info("🔕 No new listings in the top since the last notification")
        return 0

    header = f"🏆 New in the top {ALERT_TOP_N} ({session_name}): {len(new)}"
    count = 0
    for text, links in build_messages(header, new):
        if not bot_send(token, chat_id, text):  # type: ignore[arg-type]  # Bot API takes str ids
            logger.warning("⚠️  Telegram did not accept the alert; the rest is retried next run")
            break
        sent.update(links)
        save_sent(session_dir, sent)
        count += len(links)
    logger.info(f"📨 Sent {count} new listing(s) to Telegram")
    return count

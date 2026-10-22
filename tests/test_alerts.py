"""Tests for src/infrastructure/alerts.py (Telegram alerts for new top listings)"""

import pytest

from src.core.constants import ALERT_TOP_N
from src.infrastructure import alerts


def _phone(i: int, title: str | None = None) -> dict:
    return {
        "link": f"https://www.olx.kz/d/obyavlenie/phone-{i}.html",
        "title": title or f"Samsung S2{i % 10} Ultra 256",
        "price": 150_000 + i,
        "value_score": 90.0 - i,
    }


@pytest.fixture
def telegram_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:secret-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")


@pytest.fixture
def sent_messages(monkeypatch):
    """Fake tg_toolkit.bot_send that accepts every message and records it."""
    messages: list[str] = []

    def fake_send(token, chat_id, text, **_kw):
        messages.append(text)
        return True

    monkeypatch.setattr(alerts, "bot_send", fake_send)
    return messages


class TestSentState:
    def test_links_persist_across_loads(self, tmp_path):
        alerts.save_sent(tmp_path, {"a", "b"})
        alerts.save_sent(tmp_path, alerts.load_sent(tmp_path) | {"c"})
        assert alerts.load_sent(tmp_path) == {"a", "b", "c"}

    def test_sessions_do_not_share_state(self, tmp_path):
        session_a, session_b = tmp_path / "a", tmp_path / "b"
        session_a.mkdir()
        session_b.mkdir()
        alerts.save_sent(session_a, {"x"})
        assert alerts.load_sent(session_b) == set()

    def test_corrupt_state_reads_as_empty(self, tmp_path):
        (tmp_path / alerts.STATE_FILE).write_text("{not json", encoding="utf-8")
        assert alerts.load_sent(tmp_path) == set()


class TestSelectNew:
    def test_two_new_in_top(self):
        top = [_phone(i) for i in range(ALERT_TOP_N)]
        sent = {p["link"] for p in top[:8]}
        new = alerts.select_new(top, sent)
        assert [rank for rank, _ in new] == [9, 10]
        assert [p["link"] for _, p in new] == [top[8]["link"], top[9]["link"]]

    def test_nothing_new(self):
        top = [_phone(i) for i in range(ALERT_TOP_N)]
        assert alerts.select_new(top, {p["link"] for p in top}) == []

    def test_only_top_n_considered(self):
        top = [_phone(i) for i in range(ALERT_TOP_N + 5)]
        assert len(alerts.select_new(top, set())) == ALERT_TOP_N


class TestFormatting:
    def test_listing_shows_title_price_score_link(self):
        text = alerts.format_listing(3, _phone(1, "Pixel 9 Pro <b>*cheap*</b>"))
        assert "Pixel 9 Pro <b>*cheap*</b>" in text
        assert "150,001 KZT" in text
        assert "89.0" in text
        assert "https://www.olx.kz/d/obyavlenie/phone-1.html" in text

    def test_ten_long_titles_split_without_cutting_a_listing(self):
        phones = [(i + 1, _phone(i, "X" * 900)) for i in range(10)]
        messages = alerts.build_messages("header", phones)

        assert len(messages) > 1
        assert all(len(text) <= alerts.MAX_TEXT for text, _ in messages)
        # every listing is whole in exactly one message
        for _, phone in phones:
            holders = [text for text, _ in messages if phone["link"] in text]
            assert len(holders) == 1
            assert "X" * 900 in holders[0]
        assert [link for _, links in messages for link in links] == [p["link"] for _, p in phones]


class TestNotifyNewTop:
    def test_sends_new_listings_and_records_them(self, tmp_path, telegram_env, sent_messages):
        top = [_phone(i) for i in range(ALERT_TOP_N)]
        alerts.save_sent(tmp_path, {p["link"] for p in top[:8]})

        assert alerts.notify_new_top(top, tmp_path, "session") == 2
        assert len(sent_messages) == 1
        assert top[8]["link"] in sent_messages[0]
        assert top[9]["link"] in sent_messages[0]
        assert alerts.load_sent(tmp_path) == {p["link"] for p in top}

    def test_second_run_sends_nothing(self, tmp_path, telegram_env, sent_messages):
        top = [_phone(i) for i in range(ALERT_TOP_N)]
        alerts.notify_new_top(top, tmp_path, "session")
        assert alerts.notify_new_top(top, tmp_path, "session") == 0
        assert len(sent_messages) == 1

    def test_missing_token_warns_and_records_nothing(self, tmp_path, monkeypatch, sent_messages):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
        warnings: list[str] = []
        monkeypatch.setattr(alerts.logger, "warning", lambda msg, *a, **k: warnings.append(msg))

        assert alerts.notify_new_top([_phone(1)], tmp_path, "session") == 0
        assert sent_messages == []
        assert any("TELEGRAM_BOT_TOKEN" in w for w in warnings)
        assert alerts.load_sent(tmp_path) == set()

    def test_rejected_message_leaves_links_for_retry(self, tmp_path, telegram_env, monkeypatch):
        monkeypatch.setattr(alerts, "bot_send", lambda *a, **k: False)
        top = [_phone(i) for i in range(3)]

        assert alerts.notify_new_top(top, tmp_path, "session") == 0
        assert alerts.load_sent(tmp_path) == set()

    def test_partial_failure_records_only_accepted_messages(
        self, tmp_path, telegram_env, monkeypatch
    ):
        calls = []

        def send_first_only(token, chat_id, text, **_kw):
            calls.append(text)
            return len(calls) == 1

        monkeypatch.setattr(alerts, "bot_send", send_first_only)
        top = [_phone(i, "X" * 900) for i in range(ALERT_TOP_N)]

        sent = alerts.notify_new_top(top, tmp_path, "session")

        recorded = alerts.load_sent(tmp_path)
        assert 0 < sent < ALERT_TOP_N
        assert len(recorded) == sent
        assert all(link in calls[0] for link in recorded)


class TestPipelineFlag:
    """main.run_analyzer calls the notifier only with --notify, and never fails because of it."""

    @pytest.fixture
    def pipeline(self, monkeypatch):
        import main

        top = [_phone(i) for i in range(3)]

        class FakeAnalyzer:
            def __init__(self, **_kw):
                pass

            def analyze_all_androids(self, use_session_dir=True):
                return top

            def save_results(self, androids, use_session_dir=True):
                return androids

        calls: list[list[dict]] = []
        monkeypatch.setattr(main, "AndroidAnalyzer", FakeAnalyzer)
        monkeypatch.setattr(main, "notify_new_top", lambda phones, *_a: calls.append(phones))
        return main, calls, top

    def test_without_flag_no_alert(self, pipeline):
        import asyncio

        main, calls, _ = pipeline
        assert asyncio.run(main.run_analyzer()) is True
        assert calls == []

    def test_with_flag_alerts_top(self, pipeline):
        import asyncio

        main, calls, top = pipeline
        assert asyncio.run(main.run_analyzer(notify=True)) is True
        assert calls == [top]

    def test_alert_error_does_not_fail_analysis(self, pipeline, monkeypatch):
        import asyncio

        main, _, _ = pipeline

        def boom(*_a):
            raise OSError("disk full")

        monkeypatch.setattr(main, "notify_new_top", boom)
        assert asyncio.run(main.run_analyzer(notify=True)) is True

    def test_cli_accepts_notify(self, monkeypatch):
        import main

        seen = {}

        async def fake_pipeline(args):
            seen["notify"] = args.notify
            return True

        monkeypatch.setattr(main, "setup_env", lambda: None)
        monkeypatch.setattr(main, "run_pipeline", fake_pipeline)
        monkeypatch.setattr(main.logging_cfg, "configure_logging", lambda **_kw: None)
        monkeypatch.setattr("sys.argv", ["main.py", "--analyze", "--notify"])
        assert main.main() == 0
        assert seen == {"notify": True}

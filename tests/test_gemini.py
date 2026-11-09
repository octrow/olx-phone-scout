import asyncio
import json
from types import SimpleNamespace

import pytest

from src.ai import gemini
from src.ai.gemini import GeminiAnalyzer

GOOD_JSON = json.dumps(
    {
        "severity": "none",
        "is_usable": True,
        "issues_found": [],
        "bonus_points": 0,
        "bonus_reasons": [],
        "is_suspicious": False,
        "confidence": 0.9,
    }
)


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome)


class FakeAsyncModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome)


class FakeClient:
    def __init__(self, outcomes):
        self.models = FakeModels(outcomes)
        self.aio = SimpleNamespace(models=FakeAsyncModels(outcomes))


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(gemini.config, "get_session_dir", lambda: str(tmp_path))
    monkeypatch.setattr(gemini, "GEMINI_AVAILABLE", True)
    monkeypatch.setattr(gemini, "TQDM_AVAILABLE", False)
    monkeypatch.setattr(
        gemini, "types", SimpleNamespace(GenerateContentConfig=lambda **kw: kw), raising=False
    )
    monkeypatch.setattr(gemini.time, "sleep", lambda s: None)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    return tmp_path


@pytest.fixture
def sleeps(monkeypatch):
    calls = []
    monkeypatch.setattr(gemini.time, "sleep", calls.append)
    return calls


def make(outcomes=(GOOD_JSON,), **kwargs):
    analyzer = GeminiAnalyzer(**kwargs)
    analyzer.enabled = True
    analyzer.client = FakeClient(outcomes)
    return analyzer


PHONE = {"title": "iPhone 13", "price": 200000, "description": "Отличное состояние"}


class TestInit:
    def test_no_key_disables(self):
        analyzer = GeminiAnalyzer()
        assert analyzer.enabled is False
        assert analyzer.client is None

    def test_key_creates_client(self, monkeypatch):
        created = {}

        def fake_client(api_key):
            created["key"] = api_key
            return "client"

        monkeypatch.setattr(gemini, "genai", SimpleNamespace(Client=fake_client), raising=False)
        analyzer = GeminiAnalyzer(api_key="abcdefghijklmnopqrstuvwxyz")
        assert analyzer.enabled is True
        assert analyzer.client == "client"
        assert created["key"] == "abcdefghijklmnopqrstuvwxyz"

    def test_key_from_google_env(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "envkey")
        monkeypatch.setattr(
            gemini, "genai", SimpleNamespace(Client=lambda api_key: "c"), raising=False
        )
        analyzer = GeminiAnalyzer()
        assert analyzer.api_key == "envkey"
        assert analyzer.enabled is True

    def test_client_failure_disables(self, monkeypatch):
        def boom(api_key):
            raise ValueError("bad key")

        monkeypatch.setattr(gemini, "genai", SimpleNamespace(Client=boom), raising=False)
        analyzer = GeminiAnalyzer(api_key="k")
        assert analyzer.enabled is False

    def test_sdk_missing_disables(self, monkeypatch):
        monkeypatch.setattr(gemini, "GEMINI_AVAILABLE", False)
        analyzer = GeminiAnalyzer(api_key="k")
        assert analyzer.enabled is False

    def test_cache_dir_created_under_session(self, env):
        analyzer = GeminiAnalyzer()
        assert analyzer.cache_dir == env / "gemini_cache"
        assert analyzer.cache_dir.is_dir()


class TestDisabled:
    def test_analyze_listing(self):
        analyzer = GeminiAnalyzer()
        assert analyzer.analyze_listing(PHONE) == {
            "analyzed": False,
            "reason": "GenAI Client not available",
        }

    def test_analyze_batch_returns_input(self):
        analyzer = GeminiAnalyzer()
        phones = [dict(PHONE)]
        assert analyzer.analyze_batch(phones) is phones
        assert "gemini_analysis" not in phones[0]

    def test_async(self):
        analyzer = GeminiAnalyzer()
        result = asyncio.run(analyzer.analyze_listing_async(PHONE))
        assert result["analyzed"] is False


class TestPrompt:
    def test_contains_listing_fields(self):
        prompt = GeminiAnalyzer()._create_analysis_prompt(PHONE)
        assert "iPhone 13" in prompt
        assert "200000 KZT" in prompt
        assert "Отличное состояние" in prompt

    def test_empty_description_placeholder(self):
        prompt = GeminiAnalyzer()._create_analysis_prompt({"title": "X", "price": 1})
        assert "NO DESCRIPTION PROVIDED" in prompt


class TestParseJson:
    def test_plain(self):
        result = GeminiAnalyzer()._parse_json_response('  {"severity": "minor"} ')
        assert result == {"severity": "minor", "analyzed": True}

    def test_json_fence(self):
        text = 'Here:\n```json\n{"severity": "major"}\n```\nbye'
        result = GeminiAnalyzer()._parse_json_response(text)
        assert result["severity"] == "major"
        assert result["analyzed"] is True

    def test_plain_fence(self):
        result = GeminiAnalyzer()._parse_json_response('```\n{"a": 1}\n```')
        assert result == {"a": 1, "analyzed": True}

    def test_invalid_raises(self):
        with pytest.raises(json.JSONDecodeError):
            GeminiAnalyzer()._parse_json_response("not json")

    def test_async_parser_handles_fence(self):
        result = GeminiAnalyzer()._parse_async_response('```json\n{"a": 2}\n```')
        assert result == {"a": 2, "analyzed": True}


class TestPhotos:
    def test_upload_counts_successes_only(self, monkeypatch):
        responses = {
            "u1": SimpleNamespace(status_code=200, content=b"1"),
            "u2": SimpleNamespace(status_code=404, content=b""),
        }

        def fake_get(url, timeout):
            if url == "u3":
                raise ConnectionError("down")
            return responses[url]

        monkeypatch.setattr(gemini, "req_lib", SimpleNamespace(get=fake_get))
        monkeypatch.setattr(gemini, "Image", SimpleNamespace(open=lambda buf: "IMG"))
        parts, count = GeminiAnalyzer()._upload_photos_to_content(
            {"photos": ["u1", "u2", "u3"]}, "REQ"
        )
        assert parts == ["IMG"]
        assert count == 1

    def test_upload_limited_to_eight(self, monkeypatch):
        urls = []

        def fake_get(url, timeout):
            urls.append(url)
            return SimpleNamespace(status_code=200, content=b"")

        monkeypatch.setattr(gemini, "req_lib", SimpleNamespace(get=fake_get))
        monkeypatch.setattr(gemini, "Image", SimpleNamespace(open=lambda buf: "IMG"))
        _, count = GeminiAnalyzer()._upload_photos_to_content(
            {"photos": [f"u{i}" for i in range(12)]}, "REQ"
        )
        assert count == 8
        assert len(urls) == 8

    def test_photos_included_only_when_enabled(self, monkeypatch):
        monkeypatch.setattr(
            gemini,
            "req_lib",
            SimpleNamespace(get=lambda url, timeout: SimpleNamespace(status_code=200, content=b"")),
        )
        monkeypatch.setattr(gemini, "Image", SimpleNamespace(open=lambda buf: "IMG"))
        phone = {**PHONE, "photos": ["u1"]}
        assert GeminiAnalyzer()._prepare_content_parts("P", phone, "R") == ["P"]
        assert GeminiAnalyzer(use_photos=True)._prepare_content_parts("P", phone, "R") == [
            "P",
            "IMG",
        ]


class TestAnalyzeListing:
    def test_success_and_cache(self):
        analyzer = make()
        first = analyzer.analyze_listing(PHONE)
        assert first["analyzed"] is True
        assert first["severity"] == "none"
        second = analyzer.analyze_listing(PHONE)
        assert second == first
        assert len(analyzer.client.models.calls) == 1
        assert analyzer.request_count == 1

    def test_request_uses_json_mime_and_prompt(self):
        analyzer = make()
        analyzer.analyze_listing(PHONE)
        call = analyzer.client.models.calls[0]
        assert call["config"]["response_mime_type"] == "application/json"
        assert "iPhone 13" in call["contents"][0]

    def test_empty_response_is_parse_error(self, sleeps):
        analyzer = make([""])
        result = analyzer.analyze_listing(PHONE, retry_count=2)
        assert result["analyzed"] is False
        assert result["error"].startswith("JSON parsing error")
        assert sleeps == [2]

    def test_json_error_retries_then_succeeds(self, sleeps):
        analyzer = make(["garbage", GOOD_JSON])
        result = analyzer.analyze_listing(PHONE)
        assert result["analyzed"] is True
        assert sleeps == [2]
        assert len(analyzer.client.models.calls) == 2

    def test_json_error_exhausts_retries(self, sleeps):
        analyzer = make(["garbage"])
        result = analyzer.analyze_listing(PHONE, retry_count=3)
        assert result["analyzed"] is False
        assert sleeps == [2, 4]
        assert len(analyzer.client.models.calls) == 3

    def test_quota_error_is_fatal_without_retry(self, sleeps):
        analyzer = make([RuntimeError("Quota exceeded")])
        result = analyzer.analyze_listing(PHONE)
        assert result == {"analyzed": False, "error": "API quota exceeded", "fatal": True}
        assert len(analyzer.client.models.calls) == 1
        assert sleeps == []

    def test_generic_error_retries_then_reports(self, sleeps):
        analyzer = make([ValueError("boom")])
        result = analyzer.analyze_listing(PHONE, retry_count=3)
        assert result == {"analyzed": False, "error": "boom"}
        assert sleeps == [2, 4]

    def test_generic_error_then_success(self, sleeps):
        analyzer = make([ValueError("boom"), GOOD_JSON])
        assert analyzer.analyze_listing(PHONE)["analyzed"] is True

    def test_failures_are_not_cached(self, sleeps):
        analyzer = make([ValueError("boom"), GOOD_JSON])
        assert analyzer.analyze_listing(PHONE, retry_count=1)["analyzed"] is False
        assert analyzer.analyze_listing(PHONE, retry_count=1)["analyzed"] is True

    def test_request_ids_increment(self):
        analyzer = make()
        analyzer.analyze_listing({"title": "A", "price": 1})
        analyzer.analyze_listing({"title": "B", "price": 2})
        assert analyzer.request_count == 2

    def test_call_api_without_client_raises(self):
        analyzer = GeminiAnalyzer()
        with pytest.raises(RuntimeError):
            analyzer._call_gemini_api(["x"], "R")

    def test_clear_cache(self):
        analyzer = make()
        analyzer.analyze_listing(PHONE)
        analyzer.clear_cache()
        analyzer.analyze_listing(PHONE)
        assert len(analyzer.client.models.calls) == 2


class TestAnalyzeListingAsync:
    def test_success_and_cache(self):
        analyzer = make()
        first = asyncio.run(analyzer.analyze_listing_async(PHONE))
        assert first["analyzed"] is True
        second = asyncio.run(analyzer.analyze_listing_async(PHONE))
        assert second == first
        assert len(analyzer.client.aio.models.calls) == 1
        call = analyzer.client.aio.models.calls[0]
        assert "iPhone 13" in call["contents"]

    def test_no_client(self):
        analyzer = make()
        analyzer.client = None
        result = asyncio.run(analyzer.analyze_listing_async(PHONE))
        assert result == {"analyzed": False, "error": "Client not initialized"}

    def test_error_retries_then_reports(self, monkeypatch):
        delays = []

        async def fake_sleep(d):
            delays.append(d)

        monkeypatch.setattr(gemini.asyncio, "sleep", fake_sleep)
        analyzer = make([ValueError("nope")])
        result = asyncio.run(analyzer.analyze_listing_async(PHONE, retry_count=3))
        assert result == {"analyzed": False, "error": "nope"}
        assert delays == [2, 4]

    def test_error_then_success(self, monkeypatch):
        async def fake_sleep(d):
            pass

        monkeypatch.setattr(gemini.asyncio, "sleep", fake_sleep)
        analyzer = make([ValueError("nope"), GOOD_JSON])
        result = asyncio.run(analyzer.analyze_listing_async(PHONE))
        assert result["analyzed"] is True


class TestAdjustments:
    def test_bonus_applied(self):
        phone = {"value_score": 50}
        assert GeminiAnalyzer()._apply_bonus_adjustment(phone, 20) == 1
        assert phone["value_score"] == 70
        assert phone["gemini_bonus"] == 20

    def test_bonus_skipped_without_score_or_points(self):
        analyzer = GeminiAnalyzer()
        phone = {"value_score": 50}
        assert analyzer._apply_bonus_adjustment(phone, 0) == 0
        assert phone == {"value_score": 50}
        assert analyzer._apply_bonus_adjustment({}, 10) == 0

    def test_critical_penalty(self):
        phone = {"value_score": 100}
        result = GeminiAnalyzer()._apply_penalty_adjustments(
            phone, {"severity": "critical", "is_usable": False}
        )
        assert result == (1, 0)
        assert phone["value_score"] == 40
        assert phone["gemini_penalty"] == -60

    def test_critical_but_usable_not_penalised(self):
        phone = {"value_score": 100}
        result = GeminiAnalyzer()._apply_penalty_adjustments(
            phone, {"severity": "critical", "is_usable": True}
        )
        assert result == (0, 0)
        assert phone["value_score"] == 100

    def test_major_penalty(self):
        phone = {"value_score": 100}
        result = GeminiAnalyzer()._apply_penalty_adjustments(phone, {"severity": "major"})
        assert result == (0, 1)
        assert phone["value_score"] == 75
        assert phone["gemini_penalty"] == -25

    def test_suspicious_and_critical_stack(self):
        phone = {"value_score": 100}
        GeminiAnalyzer()._apply_penalty_adjustments(
            phone, {"is_suspicious": True, "severity": "critical", "is_usable": False}
        )
        assert phone["is_suspicious"] is True
        assert phone["value_score"] == 10
        assert phone["gemini_penalty"] == -90

    def test_score_floors_at_zero(self):
        phone = {"value_score": 10}
        GeminiAnalyzer()._apply_penalty_adjustments(
            phone, {"severity": "critical", "is_usable": False}
        )
        assert phone["value_score"] == 0

    def test_no_score_no_penalty(self):
        phone = {}
        result = GeminiAnalyzer()._apply_penalty_adjustments(phone, {"severity": "major"})
        assert result == (0, 0)
        assert phone == {}

    def test_process_result(self):
        analyzer = GeminiAnalyzer()
        assert analyzer._process_gemini_result({}, {"analyzed": False}) == (0, 1, 0, 0, 0)
        phone = {"value_score": 50}
        res = analyzer._process_gemini_result(
            phone, {"analyzed": True, "bonus_points": 10, "severity": "major"}
        )
        assert res == (1, 0, 1, 0, 1)
        assert phone["value_score"] == 35


class TestCheckpoint:
    def test_load_missing(self):
        assert GeminiAnalyzer()._load_checkpoint() is None

    def test_save_and_load(self):
        analyzer = GeminiAnalyzer()
        phones = [
            {"gemini_analysis": {"analyzed": True}},
            {"gemini_analysis": {"analyzed": False}},
            {"gemini_analysis": {"analyzed": True}},
        ]
        analyzer._save_checkpoint(phones, 2)
        loaded = analyzer._load_checkpoint()
        assert loaded["total_phones"] == 3
        assert loaded["current_index"] == 2
        assert loaded["successful"] == 1

    def test_load_corrupt_returns_none(self):
        analyzer = GeminiAnalyzer()
        analyzer.checkpoint_file.write_text("{broken")
        assert analyzer._load_checkpoint() is None


class TestAnalyzeBatch:
    def test_analyzes_up_to_max_and_keeps_rest(self):
        analyzer = make()
        phones = [{"title": f"P{i}", "price": i, "value_score": 50} for i in range(4)]
        result = analyzer.analyze_batch(phones, max_phones=2)
        assert len(result) == 4
        assert result[0]["gemini_analysis"]["analyzed"] is True
        assert result[1]["gemini_analysis"]["analyzed"] is True
        assert "gemini_analysis" not in result[2]
        assert len(analyzer.client.models.calls) == 2

    def test_applies_bonus_and_penalty(self):
        good = json.dumps({"severity": "none", "is_usable": True, "bonus_points": 20})
        bad = json.dumps({"severity": "critical", "is_usable": False})
        analyzer = make([good, bad])
        phones = [
            {"title": "A", "price": 1, "value_score": 50},
            {"title": "B", "price": 2, "value_score": 80},
        ]
        result = analyzer.analyze_batch(phones)
        assert result[0]["value_score"] == 70
        assert result[0]["gemini_bonus"] == 20
        assert result[1]["value_score"] == 20

    def test_failed_analysis_leaves_score(self, sleeps):
        analyzer = make([ValueError("x")])
        phones = [{"title": "A", "price": 1, "value_score": 50}]
        result = analyzer.analyze_batch(phones)
        assert result[0]["gemini_analysis"]["analyzed"] is False
        assert result[0]["value_score"] == 50

    def test_fatal_error_stops_batch(self):
        analyzer = make([RuntimeError("rate limit")])
        phones = [{"title": f"P{i}", "price": i, "value_score": 50} for i in range(3)]
        result = analyzer.analyze_batch(phones)
        assert result[0]["gemini_analysis"]["fatal"] is True
        assert "gemini_analysis" not in phones[1]
        assert "gemini_analysis" not in phones[2]
        assert len(analyzer.client.models.calls) == 1

    def test_resumes_skipping_analyzed(self):
        analyzer = make()
        analyzer.checkpoint_file.write_text(json.dumps({"current_index": 1}))
        phones = [
            {"title": "Done", "price": 1, "gemini_analysis": {"analyzed": True}},
            {"title": "Todo", "price": 2},
        ]
        result = analyzer.analyze_batch(phones)
        assert len(analyzer.client.models.calls) == 1
        assert result[0]["gemini_analysis"] == {"analyzed": True}
        assert result[1]["gemini_analysis"]["analyzed"] is True

    def test_checkpoint_removed_after_completion(self):
        analyzer = make()
        analyzer.checkpoint_file.write_text(json.dumps({"current_index": 0}))
        analyzer.analyze_batch([{"title": "A", "price": 1}])
        assert not analyzer.checkpoint_file.exists()

    def test_empty_list(self):
        analyzer = make()
        assert analyzer.analyze_batch([]) == []


class TestSummary:
    def test_not_analyzed_is_empty(self):
        analyzer = GeminiAnalyzer()
        assert analyzer.get_analysis_summary({}) == ""
        assert analyzer.get_analysis_summary({"gemini_analysis": {"analyzed": False}}) == ""

    def test_full_summary(self):
        phone = {
            "gemini_analysis": {
                "analyzed": True,
                "severity": "major",
                "bonus_points": 15,
                "bonus_reasons": ["box"],
                "is_suspicious": True,
                "suspicious_flags": ["price too low"],
                "is_usable": False,
                "issues_found": ["cracked screen"],
            }
        }
        summary = GeminiAnalyzer().get_analysis_summary(phone)
        assert "MAJOR" in summary
        assert "Bonus: +15 points" in summary
        assert "box" in summary
        assert "SUSPICIOUS" in summary
        assert "price too low" in summary
        assert "NOT USABLE" in summary
        assert "cracked screen" in summary

    def test_clean_listing_has_no_sections(self):
        phone = {"gemini_analysis": {"analyzed": True, "severity": "none", "is_usable": True}}
        summary = GeminiAnalyzer().get_analysis_summary(phone)
        assert "NONE" in summary
        assert "Bonus" not in summary
        assert "SUSPICIOUS" not in summary
        assert "NOT USABLE" not in summary
        assert "Defects" not in summary

    def test_unknown_severity(self):
        phone = {"gemini_analysis": {"analyzed": True, "is_usable": True}}
        assert "UNKNOWN" in GeminiAnalyzer().get_analysis_summary(phone)

"""logic-map #6: scrape stage success must not depend on the --phone-type filter."""

import argparse
import asyncio

import pytest


@pytest.mark.parametrize(
    ("scraped", "expected"),
    [
        (([{"link": "a"}], [], []), True),  # --phone-type iphone: androids emptied by the filter
        (([], [{"link": "a"}], []), True),
        (([], [], []), False),  # nothing scraped is still a failure
    ],
)
def test_scrape_stage_success_ignores_phone_type_filter(monkeypatch, scraped, expected):
    import main

    async def fake_scraper(_args):
        return scraped

    monkeypatch.setattr(main, "run_scraper", fake_scraper)
    args = argparse.Namespace(all=False, scrape=True, recategorize=False, analyze=False)

    assert asyncio.run(main.run_pipeline(args)) is expected

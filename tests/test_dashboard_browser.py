"""Actual headless Chromium UI interactions and responsive/keyboard smoke tests.

Required in the GitHub Actions `browser-e2e` job. Can skip in an ordinary
unit-only environment without the optional browser automation dependency.
"""
from __future__ import annotations

import shutil
import os

import pytest

from mindbench.cohort import synthetic_cohort
from mindbench.benchmark import benchmark
from mindbench.dashboard import benchmark_html

if os.environ.get("MINDBENCH_REQUIRE_BROWSER") == "1":
    # A misconfigured browser CI job must fail, never report green via a skip.
    from playwright import sync_api as playwright
else:
    playwright = pytest.importorskip("playwright.sync_api", reason="Browser suite needs Playwright")


def _launch(chromium):
    kwargs = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    # Local hosted environments may provide system Chromium rather than the
    # Playwright-managed binary; GitHub Actions installs the managed version.
    executable = shutil.which("chromium")
    if executable:
        kwargs["executable_path"] = executable
    return chromium.launch(**kwargs)


@pytest.mark.parametrize("viewport", [{"width": 1440, "height": 900}, {"width": 375, "height": 812}])
def test_benchmark_browser_controls_keyboard_and_responsiveness(viewport):
    data = benchmark(synthetic_cohort(n_subjects=12, trials_per_subject=10, seed=7), reps=10)
    html = benchmark_html(data)
    with playwright.sync_playwright() as browser_session:
        browser = _launch(browser_session.chromium)
        try:
            page = browser.new_page(viewport=viewport)
            exceptions = []
            external_requests = []
            page.on("pageerror", lambda exc: exceptions.append(str(exc)))
            page.on("request", lambda req: external_requests.append(req.url))
            page.set_content(html, wait_until="load")
            assert page.get_by_role("heading", name="Multimodal MindBench").count() == 1
            assert page.get_by_role("table").count() == 1
            assert page.locator("#metrics tr").count() == 4
            assert page.locator("#cards article").count() == 4
            assert page.get_by_role("link", name="Skip to results").count() == 1
            page.keyboard.press("Tab")
            assert page.locator(":focus").inner_text() == "Skip to results"
            page.locator("#metric").select_option("brier")
            assert page.locator("#metrics tr").count() == 4
            assert "Brier score" in page.get_by_role("combobox", name="Evaluation metric").inner_text()
            page.locator("#scope").select_option("available")
            assert page.locator("#metrics tr").count() == 1
            assert "fallback" in page.locator("#metrics").inner_text().lower()
            assert page.locator("#download").get_attribute("href").startswith("blob:")
            assert page.get_by_role("note").count() == 1
            assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
            assert not external_requests
            assert not exceptions
        finally:
            browser.close()

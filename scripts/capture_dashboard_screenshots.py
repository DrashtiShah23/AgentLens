#!/usr/bin/env python3
"""Capture polished Streamlit dashboard screenshots for README / docs."""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

DEFAULT_URL = "http://localhost:8501"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "images"
VIEWPORT_WIDTH = 1440
VIEWPORT_HEIGHT = 1100
START_HINT = (
    "Start the dashboard first with:\n"
    "  PYTHONPATH=$PWD python -m streamlit run app/dashboard/streamlit_app.py"
)


@dataclass(frozen=True)
class PageCapture:
    nav_label: str
    filename: str
    prepare: Optional[Callable] = None


def _noop_prepare(page) -> None:
    return None


def _prepare_run_review(page) -> None:
    for label in ("Failed only", "High severity", "Prompt regression"):
        try:
            page.get_by_text(label, exact=True).click(timeout=4000)
            _wait_for_page_ready(page)
            break
        except Exception:
            continue
    try:
        select = page.locator('[data-testid="stSelectbox"]').first
        select.click(timeout=4000)
        page.wait_for_timeout(400)
        options = page.locator('[data-baseweb="popover"] [role="option"]')
        if options.count() > 0:
            options.first.click(timeout=4000)
            _wait_for_page_ready(page)
    except Exception:
        pass


def _prepare_copilot(page) -> None:
    question = "Did prompt_v5_regression_case make things worse?"
    try:
        page.get_by_role("button", name=question).click(timeout=8000)
    except Exception:
        try:
            chat = page.locator('[data-testid="stChatInput"] textarea')
            chat.fill(question, timeout=4000)
            chat.press("Enter")
        except Exception:
            return
    try:
        page.wait_for_selector(".obs-response", timeout=20000)
    except Exception:
        page.wait_for_selector("text=Summary", timeout=20000)
    page.wait_for_timeout(1500)


PAGE_CAPTURES: tuple[PageCapture, ...] = (
    PageCapture("Executive Overview", "executive_overview.png"),
    PageCapture("Failure Observatory", "failure_observatory.png"),
    PageCapture("Prompt Regression Center", "prompt_regression_center.png"),
    PageCapture("Model Trust Leaderboard", "model_trust_leaderboard.png"),
    PageCapture("Run Review Center", "run_review_center.png", _prepare_run_review),
    PageCapture("Root Cause Copilot", "root_cause_copilot.png", _prepare_copilot),
)


def _ensure_server(url: str) -> None:
    try:
        urllib.request.urlopen(url, timeout=8)
    except (urllib.error.URLError, TimeoutError, OSError):
        print(f"ERROR: Streamlit dashboard is not running at {url}")
        print(START_HINT)
        sys.exit(1)


def _wait_for_page_ready(page, timeout_ms: int = 30000) -> None:
    page.wait_for_selector('[data-testid="stApp"]', timeout=timeout_ms)
    try:
        page.wait_for_selector('[data-testid="stSpinner"]', state="hidden", timeout=timeout_ms)
    except Exception:
        pass
    try:
        page.wait_for_function(
            """() => {
                const el = document.querySelector('[data-testid="stStatusWidget"]');
                return !el || getComputedStyle(el).display === 'none' || el.offsetParent === null;
            }""",
            timeout=timeout_ms,
        )
    except Exception:
        pass
    page.wait_for_timeout(1200)
    plots = page.locator(".js-plotly-plot")
    if plots.count() > 0:
        try:
            page.wait_for_function(
                "() => document.querySelectorAll('.js-plotly-plot .main-svg').length > 0",
                timeout=timeout_ms,
            )
        except Exception:
            pass
        page.wait_for_timeout(800)
    if page.locator('[data-testid="stDataFrame"]').count() > 0:
        page.wait_for_timeout(500)


def _click_nav(page, label: str) -> None:
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.get_by_text(label, exact=True).click(timeout=10000)
    _wait_for_page_ready(page)


def _screenshot_app(page, output_path: Path) -> None:
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    app = page.locator('[data-testid="stApp"]')
    app.screenshot(path=str(output_path))


def capture_screenshots(url: str, output_dir: Path) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright is not installed.")
        print("Install with:")
        print("  pip install playwright")
        print("  playwright install chromium")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    _ensure_server(url)

    saved = 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        _wait_for_page_ready(page)

        for capture in PAGE_CAPTURES:
            _click_nav(page, capture.nav_label)
            page.evaluate("window.scrollTo(0, 0)")
            if capture.prepare:
                capture.prepare(page)
            page.evaluate("window.scrollTo(0, 0)")
            _wait_for_page_ready(page)
            output_path = output_dir / capture.filename
            _screenshot_app(page, output_path)
            print(f"Saved screenshot: {output_path}")
            saved += 1

        browser.close()

    print(f"Done. {saved} screenshot(s) written to {output_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture Streamlit dashboard screenshots into docs/images.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Streamlit dashboard URL (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help=f"Output directory (default: {OUTPUT_DIR})",
    )
    args = parser.parse_args()
    return capture_screenshots(args.url, Path(args.output_dir))


if __name__ == "__main__":
    sys.exit(main())

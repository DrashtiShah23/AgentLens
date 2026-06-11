"""Lightweight validation for the screenshot capture script (no Playwright run)."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "capture_dashboard_screenshots.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("capture_dashboard_screenshots", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_capture_script_defines_six_pages():
    mod = _load_script()
    assert len(mod.PAGE_CAPTURES) == 6
    labels = {p.nav_label for p in mod.PAGE_CAPTURES}
    assert "Executive Overview" in labels
    assert "Root Cause Copilot" in labels


def test_capture_script_output_filenames():
    mod = _load_script()
    filenames = {p.filename for p in mod.PAGE_CAPTURES}
    assert filenames == {
        "executive_overview.png",
        "failure_observatory.png",
        "prompt_regression_center.png",
        "model_trust_leaderboard.png",
        "run_review_center.png",
        "root_cause_copilot.png",
    }


def test_capture_script_default_output_dir():
    mod = _load_script()
    assert mod.OUTPUT_DIR.name == "images"
    assert mod.OUTPUT_DIR.parent.name == "docs"

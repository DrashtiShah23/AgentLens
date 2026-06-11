"""Status and severity badges."""

from __future__ import annotations

from typing import Optional


def _badge(text: str, level: str) -> str:
    return f'<span class="obs-badge obs-badge-{level}">{text}</span>'


def severity_badge(severity: object = None) -> str:
    from app.dashboard.components.display_helpers import safe_lower, safe_str
    sev = safe_lower(severity)
    if not sev:
        return na_badge()
    mapping = {"critical": "critical", "high": "critical", "medium": "warning", "low": "healthy"}
    return _badge(safe_str(severity).upper(), mapping.get(sev, "info"))


def regression_badge(detected: bool = True) -> str:
    return _badge("Regression Detected" if detected else "Stable", "regression" if detected else "healthy")


def reliability_badge(score: Optional[float], threshold: float = 0.70) -> str:
    if score is None:
        return _badge("Not Applicable", "info")
    if score >= threshold:
        return _badge("Reliable", "healthy")
    if score >= 0.50:
        return _badge("Warning", "warning")
    return _badge("Risky", "critical")


def status_badge(status: str) -> str:
    return _badge(status.upper(), status if status in {"healthy", "warning", "critical"} else "info")


def success_badge(ok: bool) -> str:
    return _badge("Passed" if ok else "Failed", "healthy" if ok else "critical")


def review_badge(needs: bool) -> str:
    return _badge("Needs Review" if needs else "Auto OK", "warning" if needs else "healthy")


def na_badge() -> str:
    return _badge("Not Applicable", "info")


def execution_status_badge(success_flag: bool) -> str:
    from app.dashboard.components.display_helpers import execution_status_label
    text, level = execution_status_label(success_flag)
    return _badge(text, level)


def reliability_status_badge(
    score: Optional[float],
    failure_category: Optional[str] = None,
    severity: Optional[str] = None,
) -> str:
    from app.dashboard.components.display_helpers import reliability_status_label
    text, level = reliability_status_label(score, failure_category, severity)
    return _badge(text, level)


def task_risk_badge(reliability: Optional[float]) -> str:
    from app.dashboard.components.display_helpers import task_risk_label
    text, level = task_risk_label(reliability)
    return _badge(text, level)

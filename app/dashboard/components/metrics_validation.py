"""Validate and normalize dashboard metric values for display."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd


def normalize_rate(value: Any, *, clip: bool = True) -> Optional[float]:
    """Normalize a rate to 0.0–1.0 for display. Returns None if unavailable."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    v = float(value)
    if v > 1.0:
        if 2.0 <= v <= 100.0:
            v = v / 100.0
        elif clip:
            v = 1.0
    if v < 0.0:
        v = 0.0
    if clip and v > 1.0:
        v = 1.0
    return v


def validate_rates_in_df(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Ensure rate columns are between 0 and 1 (average rates, never summed)."""
    if df.empty:
        return df
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: normalize_rate(x))
    return out


def assert_rates_valid(df: pd.DataFrame, columns: list[str]) -> list[str]:
    """Return list of warnings if any rate exceeds 1.0 after normalization."""
    warnings: list[str] = []
    if df.empty:
        return warnings
    for col in columns:
        if col not in df.columns:
            continue
        for val in df[col].dropna():
            n = normalize_rate(val)
            if n is not None and (n < 0 or n > 1):
                warnings.append(f"{col} has out-of-range value {val}")
    return warnings

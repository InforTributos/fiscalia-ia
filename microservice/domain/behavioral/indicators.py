from __future__ import annotations

from math import isfinite


def to_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if isfinite(result) else default


def safe_ratio(numerator, denominator) -> float | None:
    den = to_float(denominator)
    if den <= 0:
        return None
    return to_float(numerator) / den


def percentile(values: list[float], pct: float) -> float:
    clean = sorted(v for v in values if isfinite(v))
    if not clean:
        return 0.0
    if len(clean) == 1:
        return clean[0]
    pct = max(0.0, min(100.0, pct))
    position = (len(clean) - 1) * pct / 100.0
    lower = int(position)
    upper = min(lower + 1, len(clean) - 1)
    weight = position - lower
    return clean[lower] * (1 - weight) + clean[upper] * weight


def median(values: list[float]) -> float:
    return percentile(values, 50)


def percentile_rank(values: list[float], target: float) -> float:
    clean = sorted(v for v in values if isfinite(v))
    if not clean:
        return 0.0
    below_or_equal = sum(1 for v in clean if v <= target)
    return round(below_or_equal / len(clean) * 100, 2)


def robust_zscore(values: list[float], target: float) -> float:
    clean = [v for v in values if isfinite(v)]
    if not clean:
        return 0.0
    med = median(clean)
    deviations = [abs(v - med) for v in clean]
    mad = median(deviations)
    if mad == 0:
        return 0.0
    return round(0.6745 * (target - med) / mad, 4)


def iqr_bounds(values: list[float]) -> tuple[float, float]:
    clean = [v for v in values if isfinite(v)]
    if not clean:
        return 0.0, 0.0
    q1 = percentile(clean, 25)
    q3 = percentile(clean, 75)
    spread = q3 - q1
    return q1 - 1.5 * spread, q3 + 1.5 * spread


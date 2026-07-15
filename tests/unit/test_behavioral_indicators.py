from domain.behavioral.indicators import (
    iqr_bounds,
    median,
    percentile,
    percentile_rank,
    robust_zscore,
    safe_ratio,
    to_float,
)


def test_to_float_with_none_returns_default():
    assert to_float(None) == 0.0
    assert to_float(None, 5.0) == 5.0


def test_to_float_with_valid_value():
    assert to_float(42) == 42.0
    assert to_float("3.14") == 3.14


def test_to_float_with_nan_returns_default():
    assert to_float(float("nan")) == 0.0


def test_safe_ratio_normal():
    assert safe_ratio(10, 2) == 5.0


def test_safe_ratio_zero_denominator():
    assert safe_ratio(10, 0) is None


def test_percentile_basic():
    assert percentile([1, 2, 3, 4, 5], 50) == 3.0


def test_median_basic():
    assert median([1, 2, 3, 4, 5]) == 3.0


def test_percentile_rank():
    assert percentile_rank([10, 20, 30], 20) == 66.67


def test_robust_zscore_outlier():
    values = [10, 12, 11, 13, 12, 100]
    z = robust_zscore(values, 100)
    assert z > 2.0


def test_iqr_bounds():
    values = list(range(1, 101))
    low, high = iqr_bounds(values)
    assert low < 25
    assert high > 75

from middleware.rate_limiter import RATE_LIMITS


def test_rate_limits_defined():
    assert "/api/v1/proceso" in RATE_LIMITS
    assert "/api/v1/analizar" in RATE_LIMITS
    assert "/api/v1/health" in RATE_LIMITS


def test_rate_limit_format():
    for path, (max_req, window) in RATE_LIMITS.items():
        assert isinstance(max_req, int)
        assert isinstance(window, int)
        assert max_req >= 0
        assert window >= 0

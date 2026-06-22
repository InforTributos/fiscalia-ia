from unittest.mock import AsyncMock

import pytest
from tasks.retry import with_retry


async def _success_fn(a, b, **kwargs):
    return a + b


async def _fail_fn(*args, **kwargs):
    raise ValueError("test error")


async def _fail_twice_then_ok(call_count=[0], *args, **kwargs):
    call_count[0] += 1
    if call_count[0] < 3:
        raise ValueError("transient error")
    return "ok"


async def test_with_retry_exito():
    result = await with_retry(_success_fn, 1, 2)
    assert result == 3


async def test_with_retry_error_permanente():
    with pytest.raises(ValueError, match="test error"):
        await with_retry(_fail_fn)


async def test_with_retry_eventual_exito():
    call_count = [0]
    result = await with_retry(
        lambda *a, **kw: _fail_twice_then_ok(call_count, *a, **kw),
        attempts=5,
        delay=0.01,
    )
    assert result == "ok"
    assert call_count[0] == 3

---
name: testing-conventions
description: Use when writing or updating tests. Covers AAA pattern, repo mocking via fixtures, PYTHONPATH setup, and coverage requirements.
---

# Testing Conventions — FiscalIA

## Required Environment
```bash
PYTHONPATH=microservice pytest tests/unit/ -v
```

`PYTHONPATH=microservice` is REQUIRED for all pytest commands.

## AAA Pattern
Every test MUST follow Arrange-Act-Assert:

```python
async def test_algo():
    # Arrange
    repo = mock_repo()
    service = MyService(repo)

    # Act
    result = await service.do_something()

    # Assert
    assert result == expected
```

## Mocking Repos
Repos are mocked via fixtures, NOT via `@patch("queries.*")`:

```python
@pytest.fixture
def mock_repo():
    repo = AsyncMock(spec=ProcesoRepo)
    repo.obtener_proceso.return_value = Proceso(...)
    return repo
```

## What to Test
- Happy path, error cases, edge cases
- All `FiscalIAError` subtypes are raised correctly
- Providers in fallback chain are called in order
- Cache hit vs cache miss

## Coverage
- Target: ≥ 80%
- Check: `PYTHONPATH=microservice pytest --cov=microservice --cov-fail-under=80`

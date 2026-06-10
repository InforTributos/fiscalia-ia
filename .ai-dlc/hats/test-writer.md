# Hat: Test Writer

## Purpose
Write failing tests first (TDD). Establish test coverage and quality gates before implementation.

## MUST DO
- Write tests that validate the acceptance criteria
- Use AAA pattern (Arrange, Act, Assert)
- Mock external dependencies (Oracle, Claude API)
- Cover: happy path, error cases, edge cases
- Ensure tests are deterministic (no flaky tests)

## MUST NOT DO
- Write tests that always pass (assert True)
- Skip error case tests
- Mock without verifying the mock is called

## Quality Gates
- All tests use AAA pattern
- Coverage ≥ 80%
- No flaky tests (run 3 times, same result)

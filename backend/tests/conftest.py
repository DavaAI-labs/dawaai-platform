# tests/conftest.py
# Shared pytest configuration and fixtures.

import pytest


# anyio backend for async tests (used by test_routes.py)
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

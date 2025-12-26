import pytest

from devtul_core import hello


def test_hello_returns_string():
    """Test that hello() returns the expected string."""
    assert hello() == "Hello from devtul-core!"

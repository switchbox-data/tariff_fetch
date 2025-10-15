"""Tests for the foo module."""

from tariff_fetch.foo import hello_world


def test_hello_world():
    """Test the hello_world function."""
    result = hello_world()
    assert result == "Hello, World!"

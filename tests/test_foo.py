"""Tests for the foo module."""

from tariff_fetch.foo import hello_world
from tariff_fetch.genability.tariffs import a


def test_hello_world():
    """Test the hello_world function."""
    result = hello_world()
    assert result == "Hello, World!"


def test_a():
    a(b="3")

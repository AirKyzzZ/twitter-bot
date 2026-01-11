"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config(temp_dir):
    """Create a sample config file."""
    config_path = temp_dir / "config.yaml"
    config_path.write_text("""
profile:
  name: "Test User"

twitter:
  api_key: "test_key"
  api_secret: "test_secret"
  access_token: "test_token"
  access_secret: "test_access_secret"

sources:
  rss_feeds:
    - url: "https://example.com/feed"
      weight: 1.0

scoring:
  boost_topics:
    - "python"
    - "ai"
  mute_topics:
    - "spam"

schedule:
  tweets_per_day: 10
  active_hours: "09:00-17:00"
  timezone: "UTC"
""")
    return config_path

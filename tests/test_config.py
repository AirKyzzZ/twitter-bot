"""Tests for configuration module."""

import os
from pathlib import Path

from twitter_bot.config import Settings, _interpolate_env_vars, load_config


def test_default_settings():
    """Test default settings creation."""
    settings = Settings()
    assert settings.schedule.tweets_per_day == 30
    assert settings.schedule.active_hours == "08:00-22:00"


def test_load_config_missing_file():
    """Test loading config when file doesn't exist."""
    settings = load_config(Path("/nonexistent/config.yaml"))
    assert isinstance(settings, Settings)


def test_load_config_from_file(sample_config):
    """Test loading config from YAML file."""
    settings = load_config(sample_config)
    assert settings.profile.name == "Test User"
    assert settings.schedule.tweets_per_day == 10
    assert len(settings.scoring.boost_topics) == 2


def test_interpolate_env_vars():
    """Test environment variable interpolation."""
    os.environ["TEST_VAR"] = "test_value"

    data = {"key": "${TEST_VAR}"}
    result = _interpolate_env_vars(data)

    assert result["key"] == "test_value"

    del os.environ["TEST_VAR"]


def test_interpolate_env_vars_nested():
    """Test nested env var interpolation."""
    os.environ["NESTED_VAR"] = "nested_value"

    data = {
        "outer": {
            "inner": "${NESTED_VAR}",
            "list": ["${NESTED_VAR}", "static"],
        }
    }
    result = _interpolate_env_vars(data)

    assert result["outer"]["inner"] == "nested_value"
    assert result["outer"]["list"][0] == "nested_value"
    assert result["outer"]["list"][1] == "static"

    del os.environ["NESTED_VAR"]

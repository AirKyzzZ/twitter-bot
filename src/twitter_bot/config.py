"""Configuration management using Pydantic Settings."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from twitter_bot.exceptions import ConfigError

# Load environment variables from .env file
load_dotenv()


class TwitterConfig(BaseModel):
    """Twitter API configuration."""

    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    access_secret: str = ""
    bearer_token: str = ""


class SourceConfig(BaseModel):
    """RSS feed source configuration."""

    url: str
    weight: float = 1.0


class ScoringConfig(BaseModel):
    """Content scoring configuration."""

    boost_topics: list[str] = Field(default_factory=list)
    mute_topics: list[str] = Field(default_factory=list)


class ScheduleConfig(BaseModel):
    """Daemon scheduling configuration."""

    tweets_per_day: int = 30
    active_hours: str = "08:00-22:00"
    timezone: str = "UTC"


class ReplyConfig(BaseModel):
    """Reply bot configuration."""

    enabled: bool = True
    max_per_day: int = 40
    min_delay_seconds: int = 120  # 2 min between replies
    max_delay_seconds: int = 300  # 5 min max
    target_min_followers: int = 1000
    target_max_followers: int = 500000
    min_engagement_score: int = 5
    score_threshold: float = 0.6  # Min score to consider replying
    watch_interval_seconds: int = 45  # How often to check timeline
    topics: list[str] = Field(default_factory=list)  # Override boost_topics
    cookies_path: str = "~/.twitter-bot/cookies.json"


class PosterConfig(BaseModel):
    """Poster bot configuration (original tweet posting)."""

    max_per_day: int = 10
    allow_threads: bool = False


class ProfileConfig(BaseModel):
    """User profile configuration."""

    name: str = ""
    voice_file: str = ""


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_prefix="TWITTER_BOT_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Core settings
    profile: ProfileConfig = Field(default_factory=ProfileConfig)
    twitter: TwitterConfig = Field(default_factory=TwitterConfig)
    sources: list[SourceConfig] = Field(default_factory=list)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    reply: ReplyConfig = Field(default_factory=ReplyConfig)
    poster: PosterConfig = Field(default_factory=PosterConfig)

    # LLM settings
    gemini_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""

    # Paths
    data_dir: Path = Path.home() / ".twitter-bot"

    @property
    def state_file(self) -> Path:
        return self.data_dir / "state.json"

    @property
    def queue_file(self) -> Path:
        return self.data_dir / "queue.json"


def _interpolate_env_vars(data: Any) -> Any:
    """Recursively interpolate ${VAR} patterns with environment variables."""
    if isinstance(data, str):
        if data.startswith("${") and data.endswith("}"):
            var_name = data[2:-1]
            return os.environ.get(var_name, "")
        return data
    elif isinstance(data, dict):
        return {k: _interpolate_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_interpolate_env_vars(item) for item in data]
    return data


def load_config(config_path: Path | None = None) -> Settings:
    """Load configuration from YAML file with env var interpolation."""
    if config_path is None:
        # Check current directory first, then home directory
        local_config = Path("config.yaml")
        if local_config.exists():
            config_path = local_config
        else:
            config_path = Path.home() / ".twitter-bot" / "config.yaml"

    if not config_path.exists():
        # Return defaults if no config file
        return Settings()

    try:
        with open(config_path) as f:
            raw_config = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}") from e

    # Interpolate environment variables
    config_data = _interpolate_env_vars(raw_config)

    # Convert RSS feeds to SourceConfig list
    if "sources" in config_data and "rss_feeds" in config_data["sources"]:
        config_data["sources"] = config_data["sources"]["rss_feeds"]

    try:
        return Settings(**config_data)
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}") from e


# Global settings instance (lazy loaded)
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = load_config()
    return _settings

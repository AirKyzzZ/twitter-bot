"""JSON-based state persistence for deduplication and history."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from twitter_bot.exceptions import StateError


@dataclass
class PostedTweet:
    """Record of a posted tweet."""

    tweet_id: str
    content: str
    content_hash: str
    source_url: str | None
    posted_at: str  # ISO format
    source_title: str | None = None


@dataclass
class State:
    """Application state."""

    posted_tweets: list[PostedTweet] = field(default_factory=list)
    content_hashes: set[str] = field(default_factory=set)
    processed_urls: set[str] = field(default_factory=set)
    recent_topics: list[str] = field(default_factory=list)  # Track last N topics
    last_run: str | None = None


class StateManager:
    """Manages JSON state persistence."""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self._state: State | None = None

    def _ensure_dir(self) -> None:
        """Ensure the state directory exists."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> State:
        """Load state from JSON file."""
        if self._state is not None:
            return self._state

        if not self.state_file.exists():
            self._state = State()
            return self._state

        try:
            with open(self.state_file) as f:
                data = json.load(f)

            posted_tweets = [PostedTweet(**tweet) for tweet in data.get("posted_tweets", [])]
            self._state = State(
                posted_tweets=posted_tweets,
                content_hashes=set(data.get("content_hashes", [])),
                processed_urls=set(data.get("processed_urls", [])),
                recent_topics=data.get("recent_topics", []),
                last_run=data.get("last_run"),
            )
            return self._state
        except json.JSONDecodeError as e:
            raise StateError(f"Corrupted state file: {e}") from e
        except Exception as e:
            raise StateError(f"Failed to load state: {e}") from e

    def save(self) -> None:
        """Save state to JSON file."""
        if self._state is None:
            return

        self._ensure_dir()

        data = {
            "posted_tweets": [
                {
                    "tweet_id": t.tweet_id,
                    "content": t.content,
                    "content_hash": t.content_hash,
                    "source_url": t.source_url,
                    "posted_at": t.posted_at,
                    "source_title": t.source_title,
                }
                for t in self._state.posted_tweets
            ],
            "content_hashes": list(self._state.content_hashes),
            "processed_urls": list(self._state.processed_urls),
            "recent_topics": self._state.recent_topics,
            "last_run": self._state.last_run,
        }

        try:
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise StateError(f"Failed to save state: {e}") from e

    def content_hash(self, content: str) -> str:
        """Generate a hash for content deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def is_duplicate(self, content: str) -> bool:
        """Check if content has already been posted."""
        state = self.load()
        content_hash = self.content_hash(content)
        return content_hash in state.content_hashes

    def is_url_processed(self, url: str) -> bool:
        """Check if a URL has already been processed."""
        state = self.load()
        return url in state.processed_urls

    def mark_url_processed(self, url: str) -> None:
        """Mark a URL as processed."""
        state = self.load()
        state.processed_urls.add(url)
        self.save()

    def record_tweet(
        self,
        tweet_id: str,
        content: str,
        source_url: str | None = None,
        source_title: str | None = None,
    ) -> None:
        """Record a posted tweet."""
        state = self.load()
        content_hash = self.content_hash(content)

        posted = PostedTweet(
            tweet_id=tweet_id,
            content=content,
            content_hash=content_hash,
            source_url=source_url,
            posted_at=datetime.utcnow().isoformat(),
            source_title=source_title,
        )

        state.posted_tweets.append(posted)
        state.content_hashes.add(content_hash)
        if source_url:
            state.processed_urls.add(source_url)

        self.save()

    def update_last_run(self) -> None:
        """Update the last run timestamp."""
        state = self.load()
        state.last_run = datetime.utcnow().isoformat()
        self.save()

    def get_recent_tweets(self, limit: int = 10) -> list[PostedTweet]:
        """Get the most recent posted tweets."""
        state = self.load()
        return state.posted_tweets[-limit:]

    def record_topic(self, topic: str, max_history: int = 10) -> None:
        """Record a topic as recently used."""
        state = self.load()
        state.recent_topics.append(topic)
        # Keep only last N topics
        state.recent_topics = state.recent_topics[-max_history:]
        self.save()

    def get_recent_topics(self, limit: int = 10) -> list[str]:
        """Get recently used topics."""
        state = self.load()
        return state.recent_topics[-limit:]

    def select_topic_with_rotation(self, available_topics: list[str]) -> str:
        """Select a topic, avoiding recently used ones."""
        import random

        state = self.load()
        recent = set(state.recent_topics[-10:])  # Last 10 topics to avoid

        # Filter out recent topics
        fresh_topics = [t for t in available_topics if t not in recent]

        # If all topics are recent, use topics not in last 5
        if not fresh_topics:
            very_recent = set(state.recent_topics[-5:])
            fresh_topics = [t for t in available_topics if t not in very_recent]

        # Fallback to all topics if still empty
        if not fresh_topics:
            fresh_topics = available_topics

        return random.choice(fresh_topics)

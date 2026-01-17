"""JSON-based state persistence for deduplication and history."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
class RepliedTweet:
    """Record of a reply to another tweet."""

    original_tweet_id: str
    original_author: str
    original_content: str
    reply_tweet_id: str
    reply_content: str
    reply_type: str  # expert, contrarian, question, story, simplifier
    replied_at: str  # ISO format


@dataclass
class State:
    """Application state."""

    posted_tweets: list[PostedTweet] = field(default_factory=list)
    content_hashes: set[str] = field(default_factory=set)
    processed_urls: set[str] = field(default_factory=set)
    recent_topics: list[str] = field(default_factory=list)  # Track last N topics
    last_run: str | None = None
    # Reply bot state
    replied_tweets: list[RepliedTweet] = field(default_factory=list)
    replied_tweet_ids: set[str] = field(default_factory=set)
    reply_type_history: list[str] = field(default_factory=list)  # For rotation
    last_reply_at: str | None = None


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
            replied_tweets = [RepliedTweet(**tweet) for tweet in data.get("replied_tweets", [])]
            self._state = State(
                posted_tweets=posted_tweets,
                content_hashes=set(data.get("content_hashes", [])),
                processed_urls=set(data.get("processed_urls", [])),
                recent_topics=data.get("recent_topics", []),
                last_run=data.get("last_run"),
                # Reply bot state
                replied_tweets=replied_tweets,
                replied_tweet_ids=set(data.get("replied_tweet_ids", [])),
                reply_type_history=data.get("reply_type_history", []),
                last_reply_at=data.get("last_reply_at"),
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
            # Reply bot state
            "replied_tweets": [
                {
                    "original_tweet_id": r.original_tweet_id,
                    "original_author": r.original_author,
                    "original_content": r.original_content,
                    "reply_tweet_id": r.reply_tweet_id,
                    "reply_content": r.reply_content,
                    "reply_type": r.reply_type,
                    "replied_at": r.replied_at,
                }
                for r in self._state.replied_tweets
            ],
            "replied_tweet_ids": list(self._state.replied_tweet_ids),
            "reply_type_history": self._state.reply_type_history,
            "last_reply_at": self._state.last_reply_at,
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

    # Reply bot methods

    def is_tweet_replied(self, tweet_id: str) -> bool:
        """Check if we've already replied to this tweet."""
        state = self.load()
        return tweet_id in state.replied_tweet_ids

    def record_reply(self, replied: RepliedTweet) -> None:
        """Record a reply to a tweet."""
        state = self.load()
        state.replied_tweets.append(replied)
        state.replied_tweet_ids.add(replied.original_tweet_id)
        state.reply_type_history.append(replied.reply_type)
        # Keep only last 50 reply types for rotation
        state.reply_type_history = state.reply_type_history[-50:]
        state.last_reply_at = replied.replied_at
        self.save()

    def get_replies_today_count(self, timezone: str = "UTC") -> int:
        """Get the number of replies posted today in the given timezone."""
        from zoneinfo import ZoneInfo

        state = self.load()
        try:
            local_tz = ZoneInfo(timezone)
        except Exception:
            local_tz = UTC

        now = datetime.now(local_tz)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        count = 0
        for reply in state.replied_tweets:
            try:
                replied_at = datetime.fromisoformat(reply.replied_at)
                # Assume UTC if no timezone info
                if replied_at.tzinfo is None:
                    replied_at = replied_at.replace(tzinfo=UTC)
                replied_local = replied_at.astimezone(local_tz)
                if replied_local >= today_start:
                    count += 1
            except Exception:
                continue
        return count

    def get_next_reply_type(self) -> str:
        """Get the next reply type, rotating through available types."""
        reply_types = ["expert", "contrarian", "question", "story", "simplifier"]
        state = self.load()

        if not state.reply_type_history:
            # First reply - start with expert
            return reply_types[0]

        # Count recent usage (last 10)
        recent = state.reply_type_history[-10:]
        counts = {t: recent.count(t) for t in reply_types}

        # Pick the least used type
        min_count = min(counts.values())
        least_used = [t for t, c in counts.items() if c == min_count]

        # If multiple tied, avoid the most recent one
        if len(least_used) > 1 and state.reply_type_history:
            last_type = state.reply_type_history[-1]
            least_used = [t for t in least_used if t != last_type] or least_used

        import random

        return random.choice(least_used)

    def can_reply_now(self, min_delay_seconds: int) -> bool:
        """Check if enough time has passed since the last reply."""
        state = self.load()
        if state.last_reply_at is None:
            return True

        try:
            last_reply = datetime.fromisoformat(state.last_reply_at)
            # Ensure timezone-aware comparison
            if last_reply.tzinfo is None:
                last_reply = last_reply.replace(tzinfo=UTC)
            elapsed = (datetime.now(UTC) - last_reply).total_seconds()
            return elapsed >= min_delay_seconds
        except Exception:
            return True

    def get_recent_replies(self, limit: int = 10) -> list[RepliedTweet]:
        """Get the most recent replies."""
        state = self.load()
        return state.replied_tweets[-limit:]

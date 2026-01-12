"""RSS feed client for content ingestion."""

from dataclasses import dataclass
from datetime import datetime

import feedparser
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from twitter_bot.exceptions import SourceError


@dataclass
class FeedItem:
    """Parsed RSS feed item."""

    title: str
    url: str
    summary: str
    published: datetime | None
    source_feed: str


class RSSClient:
    """Client for fetching and parsing RSS feeds."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "RSSClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def fetch_feed(self, url: str) -> list[FeedItem]:
        """Fetch and parse an RSS feed."""
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise SourceError(f"Failed to fetch RSS feed {url}: {e}") from e

        try:
            feed = feedparser.parse(response.text)
        except Exception as e:
            raise SourceError(f"Failed to parse RSS feed {url}: {e}") from e

        items = []
        for entry in feed.entries:
            # Parse published date
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6])
                except (TypeError, ValueError):
                    pass

            # Get summary, falling back to content
            summary = ""
            if hasattr(entry, "summary"):
                summary = entry.summary
            elif hasattr(entry, "content") and entry.content:
                summary = entry.content[0].get("value", "")

            items.append(
                FeedItem(
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    summary=summary,
                    published=published,
                    source_feed=url,
                )
            )

        return items

    def fetch_multiple(self, feeds: list[tuple[str, float]]) -> list[tuple[FeedItem, float]]:
        """Fetch multiple feeds and return items with their weights.

        Args:
            feeds: List of (url, weight) tuples

        Returns:
            List of (FeedItem, weight) tuples
        """
        results = []
        for url, weight in feeds:
            try:
                items = self.fetch_feed(url)
                for item in items:
                    results.append((item, weight))
            except SourceError:
                # Log and continue - don't let one feed failure stop others
                continue
        return results

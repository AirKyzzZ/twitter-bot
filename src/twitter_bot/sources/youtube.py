"""YouTube transcript extractor."""

import re
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from twitter_bot.exceptions import SourceError


@dataclass
class YouTubeContent:
    """Extracted YouTube video content."""

    video_id: str
    url: str
    title: str
    description: str
    transcript: str | None


class YouTubeExtractor:
    """Extracts content from YouTube videos."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "YouTubeExtractor":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL."""
        patterns = [
            r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
            r"(?:embed/)([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise SourceError(f"Could not extract video ID from URL: {url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def extract(self, url: str) -> YouTubeContent:
        """Extract content from a YouTube video."""
        video_id = self._extract_video_id(url)

        # Fetch video page to get title and description
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            response = self._client.get(video_url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise SourceError(f"Failed to fetch YouTube video {url}: {e}") from e

        html = response.text

        # Extract title
        title = self._extract_title(html)

        # Extract description
        description = self._extract_description(html)

        # Try to get transcript (basic implementation - would need
        # youtube-transcript-api for full support)
        transcript = None

        return YouTubeContent(
            video_id=video_id,
            url=video_url,
            title=title,
            description=description,
            transcript=transcript,
        )

    def _extract_title(self, html: str) -> str:
        """Extract video title from HTML."""
        match = re.search(r'"title":"([^"]+)"', html)
        if match:
            return match.group(1)

        match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
        if match:
            title = match.group(1)
            # Remove " - YouTube" suffix
            return re.sub(r"\s*-\s*YouTube\s*$", "", title)

        return ""

    def _extract_description(self, html: str) -> str:
        """Extract video description from HTML."""
        match = re.search(r'"shortDescription":"([^"]*)"', html)
        if match:
            # Unescape JSON string
            desc = match.group(1)
            desc = desc.replace("\\n", "\n").replace('\\"', '"')
            return desc[:2000]  # Limit length
        return ""

"""Web page content extractor."""

import re
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from twitter_bot.exceptions import SourceError


@dataclass
class WebContent:
    """Extracted web page content."""

    url: str
    title: str
    content: str
    description: str | None


class WebExtractor:
    """Extracts content from web pages."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; TwitterBot/1.0)"
            },
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "WebExtractor":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def extract(self, url: str) -> WebContent:
        """Extract content from a web page."""
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise SourceError(f"Failed to fetch URL {url}: {e}") from e

        html = response.text

        # Extract title
        title = self._extract_title(html)

        # Extract meta description
        description = self._extract_meta_description(html)

        # Extract main content (basic extraction)
        content = self._extract_content(html)

        return WebContent(
            url=url,
            title=title,
            content=content,
            description=description,
        )

    def _extract_title(self, html: str) -> str:
        """Extract page title from HTML."""
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_meta_description(self, html: str) -> str | None:
        """Extract meta description from HTML."""
        match = re.search(
            r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        # Try og:description
        match = re.search(
            r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        return None

    def _extract_content(self, html: str) -> str:
        """Extract main text content from HTML (basic implementation)."""
        # Remove script and style tags
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        # Limit to first 5000 chars for LLM context
        return text[:5000]

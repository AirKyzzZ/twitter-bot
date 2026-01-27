"""Image generation for tweets.

DATA-DRIVEN: Media (image/video) gets 2x boost vs text-only tweets.
Strategy: Auto-generate relevant images when [IMAGE: description] is suggested.

Supported sources:
1. Unsplash (free, high-quality stock photos)
2. Code screenshots (for tech takes)
3. Simple text cards (for quotes/stats)
"""

import logging
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx

logger = logging.getLogger(__name__)


@dataclass
class GeneratedImage:
    """A generated or fetched image."""
    
    path: Path
    source: str  # "unsplash", "code_screenshot", "text_card"
    description: str
    width: int
    height: int


# Keywords that suggest code screenshot would be better
CODE_KEYWORDS = [
    "code", "snippet", "function", "bug", "error", "console",
    "terminal", "typescript", "python", "javascript", "rust",
    "api", "json", "syntax", "debug", "log", "output",
]

# Unsplash topics for tech content
TECH_TOPICS = [
    "technology", "coding", "computer", "programming", "startup",
    "office", "desk", "laptop", "developer", "software",
]


class ImageGenerator:
    """Generate or fetch images for tweets based on description."""

    def __init__(
        self,
        unsplash_access_key: str | None = None,
        output_dir: Path | None = None,
    ):
        """Initialize image generator.
        
        Args:
            unsplash_access_key: Unsplash API key (optional, uses demo if not provided)
            output_dir: Directory to save generated images
        """
        self.unsplash_key = unsplash_access_key
        self.output_dir = output_dir or Path(tempfile.gettempdir()) / "twitter-bot-images"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def parse_image_suggestion(self, text: str) -> str | None:
        """Extract image description from [IMAGE: description] tag.
        
        Args:
            text: Tweet content with potential [IMAGE: ...] tag
            
        Returns:
            Image description or None if no tag found
        """
        match = re.search(r"\[IMAGE:\s*([^\]]+)\]", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def remove_image_tag(self, text: str) -> str:
        """Remove [IMAGE: ...] tag from text."""
        return re.sub(r"\s*\[IMAGE:[^\]]+\]", "", text, flags=re.IGNORECASE).strip()

    def _detect_image_type(self, description: str) -> Literal["code", "unsplash", "text"]:
        """Detect what type of image would best match the description."""
        desc_lower = description.lower()
        
        # Check for code-related keywords
        if any(kw in desc_lower for kw in CODE_KEYWORDS):
            return "code"
        
        # Check for quote/stat card keywords
        if any(kw in desc_lower for kw in ["quote", "stat", "number", "percentage", "%"]):
            return "text"
        
        # Default to Unsplash for general images
        return "unsplash"

    def generate_from_description(
        self,
        description: str,
        tweet_content: str | None = None,
    ) -> GeneratedImage | None:
        """Generate or fetch an image based on description.
        
        Args:
            description: Image description from [IMAGE: ...] tag
            tweet_content: Optional tweet content for context
            
        Returns:
            GeneratedImage or None if generation fails
        """
        image_type = self._detect_image_type(description)
        
        if image_type == "code" and tweet_content:
            # Try to generate code screenshot
            from twitter_bot.images.code_screenshot import CodeScreenshotGenerator
            code_gen = CodeScreenshotGenerator(self.output_dir)
            return code_gen.generate_from_tweet(tweet_content, description)
        
        # Default: fetch from Unsplash
        return self._fetch_unsplash(description)

    def _fetch_unsplash(self, query: str) -> GeneratedImage | None:
        """Fetch a relevant image from Unsplash.
        
        Args:
            query: Search query for image
            
        Returns:
            GeneratedImage or None if fetch fails
        """
        # Clean query for search
        clean_query = re.sub(r"[^\w\s]", "", query)[:50]
        
        # If no API key, use fallback topics
        if not self.unsplash_key:
            logger.warning("No Unsplash API key, using random tech image")
            clean_query = "technology coding"
        
        try:
            # Use Unsplash source API (no key needed for random images)
            # This gives us a random image matching the query
            image_url = f"https://source.unsplash.com/1200x675/?{clean_query.replace(' ', ',')}"
            
            with httpx.Client(follow_redirects=True, timeout=30) as client:
                response = client.get(image_url)
                response.raise_for_status()
                
                # Save to file
                filename = f"unsplash_{hash(query) % 10000}.jpg"
                filepath = self.output_dir / filename
                filepath.write_bytes(response.content)
                
                return GeneratedImage(
                    path=filepath,
                    source="unsplash",
                    description=query,
                    width=1200,
                    height=675,
                )
                
        except Exception as e:
            logger.error(f"Unsplash fetch failed: {e}")
            return None

    def generate_for_tweet(
        self,
        tweet_content: str,
    ) -> tuple[str, GeneratedImage | None]:
        """Process a tweet and generate image if [IMAGE: ...] tag present.
        
        Args:
            tweet_content: Full tweet content with potential image tag
            
        Returns:
            Tuple of (cleaned_content, GeneratedImage or None)
        """
        description = self.parse_image_suggestion(tweet_content)
        
        if not description:
            return (tweet_content, None)
        
        # Remove the tag from content
        clean_content = self.remove_image_tag(tweet_content)
        
        # Generate the image
        image = self.generate_from_description(description, clean_content)
        
        return (clean_content, image)

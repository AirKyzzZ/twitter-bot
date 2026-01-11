"""Content relevance scoring."""

import re
from dataclasses import dataclass


@dataclass
class ScoredContent:
    """Content with relevance score."""

    title: str
    url: str
    content: str
    score: float
    source_weight: float
    matched_boost_topics: list[str]
    matched_mute_topics: list[str]


class ContentScorer:
    """Scores content based on relevance to configured topics."""

    def __init__(
        self,
        boost_topics: list[str] | None = None,
        mute_topics: list[str] | None = None,
    ):
        self.boost_topics = [t.lower() for t in (boost_topics or [])]
        self.mute_topics = [t.lower() for t in (mute_topics or [])]

    def _find_topic_matches(self, text: str, topics: list[str]) -> list[str]:
        """Find which topics appear in the text."""
        text_lower = text.lower()
        matches = []
        for topic in topics:
            # Simple word boundary matching
            pattern = r"\b" + re.escape(topic) + r"\b"
            if re.search(pattern, text_lower):
                matches.append(topic)
        return matches

    def score(
        self,
        title: str,
        url: str,
        content: str,
        source_weight: float = 1.0,
    ) -> ScoredContent:
        """Score content based on topic relevance.

        Scoring logic:
        - Base score: 1.0
        - Each boost topic match: +0.5 (title) or +0.2 (content)
        - Each mute topic match: -1.0 (effectively filters)
        - Multiply by source weight

        Args:
            title: Content title
            url: Content URL
            content: Content body text
            source_weight: Weight from the source feed

        Returns:
            ScoredContent with relevance score
        """
        combined_text = f"{title} {content}"

        # Find topic matches
        boost_matches = self._find_topic_matches(combined_text, self.boost_topics)
        mute_matches = self._find_topic_matches(combined_text, self.mute_topics)

        # Calculate score
        score = 1.0

        # Boost topics in title are worth more
        title_boost_matches = self._find_topic_matches(title, self.boost_topics)
        content_boost_matches = [m for m in boost_matches if m not in title_boost_matches]

        score += len(title_boost_matches) * 0.5
        score += len(content_boost_matches) * 0.2

        # Mute topics heavily penalize
        score -= len(mute_matches) * 1.0

        # Apply source weight
        score *= source_weight

        # Floor at 0
        score = max(0.0, score)

        return ScoredContent(
            title=title,
            url=url,
            content=content,
            score=score,
            source_weight=source_weight,
            matched_boost_topics=boost_matches,
            matched_mute_topics=mute_matches,
        )

    def score_and_filter(
        self,
        items: list[tuple[str, str, str, float]],
        min_score: float = 0.5,
    ) -> list[ScoredContent]:
        """Score multiple items and filter by minimum score.

        Args:
            items: List of (title, url, content, source_weight) tuples
            min_score: Minimum score to include

        Returns:
            List of ScoredContent, sorted by score descending
        """
        scored = [
            self.score(title, url, content, weight)
            for title, url, content, weight in items
        ]

        # Filter by minimum score and mute topics
        filtered = [
            s for s in scored
            if s.score >= min_score and not s.matched_mute_topics
        ]

        # Sort by score descending
        return sorted(filtered, key=lambda x: x.score, reverse=True)

    def select_best(
        self,
        items: list[tuple[str, str, str, float]],
        processed_urls: set[str] | None = None,
    ) -> ScoredContent | None:
        """Select the best unprocessed content item.

        Args:
            items: List of (title, url, content, source_weight) tuples
            processed_urls: Set of already processed URLs to skip

        Returns:
            Best ScoredContent or None if all filtered
        """
        processed = processed_urls or set()
        scored = self.score_and_filter(items)

        for item in scored:
            if item.url not in processed:
                return item

        return None

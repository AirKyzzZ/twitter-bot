"""Reply generation using LLM with viral prompt framework."""

import logging

from twitter_bot.browser.watcher import ScrapedTweet
from twitter_bot.generation.provider import LLMProvider
from twitter_bot.state.manager import StateManager

logger = logging.getLogger(__name__)

# Available reply types for rotation
REPLY_TYPES = ["witty", "agree_twist", "hot_take", "one_liner", "flex"]

# Instructions for each reply type
REPLY_TYPE_INSTRUCTIONS = {
    "witty": """Quick joke, clever observation, or punchline.
Keep it SHORT and natural. Don't try too hard.""",
    "agree_twist": """Agree with their point but add an unexpected angle.
Short validation + your addition.""",
    "hot_take": """Drop a spicy but genuine opinion.
Direct, slightly provocative, but not mean or forced.""",
    "one_liner": """Minimal response - just a few words that hit.
Sometimes less is more. Can be just 2-5 words.""",
    "flex": """Share relevant experience or knowledge casually.
Not braggy - just naturally adding context from your work.""",
}


class ReplyGenerator:
    """Generates viral replies using LLM."""

    def __init__(
        self,
        provider: LLMProvider,
        voice_profile: str,
        state: StateManager,
    ):
        """Initialize the reply generator.

        Args:
            provider: LLM provider for generation
            voice_profile: Voice/persona description for consistent tone
            state: StateManager for reply type rotation
        """
        self.provider = provider
        self.voice_profile = voice_profile
        self.state = state

    def generate_reply(self, tweet: ScrapedTweet) -> tuple[str, str]:
        """Generate a reply for a tweet.

        Args:
            tweet: The tweet to reply to

        Returns:
            Tuple of (reply_text, reply_type)
        """
        # Get next reply type from rotation
        reply_type = self.state.get_next_reply_type()

        # Build the prompt
        prompt = self._build_prompt(tweet, reply_type)

        # Generate reply
        logger.debug(f"Generating {reply_type} reply for tweet {tweet.tweet_id}")
        result = self.provider.generate(prompt, max_tokens=150)

        # Clean up the reply
        reply = self._clean_reply(result.text)

        # Validate length
        if len(reply) > 280:
            logger.warning(f"Reply too long ({len(reply)} chars), truncating")
            reply = reply[:277] + "..."

        logger.info(f"Generated {reply_type} reply: {reply[:50]}...")
        return reply, reply_type

    def _build_prompt(self, tweet: ScrapedTweet, reply_type: str) -> str:
        """Build the reply generation prompt.

        Args:
            tweet: The tweet to reply to
            reply_type: The type of reply to generate

        Returns:
            Complete prompt string
        """
        return f"""you're maxime. 19yo french dev from bordeaux. you build stuff with AI, next.js, typescript. you ship fast.

your twitter style:
- lowercase always
- SHORT replies (5-20 words max)
- witty, clever, sometimes dry humor
- casual but not trying too hard
- emojis sparingly - only when they really add something (🤣 💸 🇫🇷)
- no corporate speak, no linkedin energy
- sometimes just a quick observation or hot take
- french references occasionally (not forced)

vibe examples (for inspiration, don't copy):
- quick agreement + twist: "and FOMO for sure"
- spicy one-liner: "study comp sci" (answering "fastest way to go broke")
- minimal: "true" or "exactly"
- dry observation: "they just accepted that they won't train a model"
- genuine take: "everyone is joking about google fumbling but the product is actually good"
- relatable dev humor: "how can you explain her it's the best feeling ever"

---
TWEET:
@{tweet.author_handle}: {tweet.content}
---

reply type: {reply_type}
{REPLY_TYPE_INSTRUCTIONS[reply_type]}

RULES:
- BE SHORT. 5-20 words ideal. sometimes even 2-3 words is perfect.
- lowercase
- no hashtags, no links
- vary your style - don't repeat patterns
- sound natural, like texting a friend
- NO EMOJIS most of the time. only use one if it genuinely adds something (like 1 in 10 replies max)
- no forced french references either - only when actually relevant
- add genuine value or humor, not empty agreement

just the reply, nothing else."""

    def _clean_reply(self, text: str) -> str:
        """Clean up LLM output.

        Args:
            text: Raw LLM output

        Returns:
            Cleaned reply text
        """
        text = text.strip()

        # Remove quotes if wrapped
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        if text.startswith("'") and text.endswith("'"):
            text = text[1:-1]

        # Remove any "Reply:" or similar prefix
        prefixes = ["reply:", "response:", "answer:"]
        for prefix in prefixes:
            if text.lower().startswith(prefix):
                text = text[len(prefix) :].strip()

        # Remove any trailing quotes or punctuation artifacts
        text = text.strip('"\'')

        return text.strip()

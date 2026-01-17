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
    "witty": """Add a quick joke or punchline that lands.
Keep it SHORT. Max 10-15 words.
Example vibe: "how can you explain her it's the best feeling ever" """,
    "agree_twist": """Quick agreement + unexpected angle or addition.
Pattern: short take + twist
Example vibe: "and FOMO for sure" or "they just accepted that they won't train a model" """,
    "hot_take": """Drop a spicy opinion in few words.
Be direct, slightly provocative but not mean.
Example vibe: "study comp sci" (as answer to "fastest way to go broke") """,
    "one_liner": """Just a few words that hit hard.
Sometimes just one word + emoji is perfect.
Example vibe: "true" or "french 🇫🇷" or "PRO but 💸" """,
    "flex": """Subtle flex about your experience/knowledge without being cringe.
Keep it casual, not braggy.
Example vibe: "a cracked engineer learning marketing is so gold bro it's not even close" """,
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

your vibe on twitter:
- lowercase always
- SHORT replies (3-20 words max, often just 5-10)
- witty, quick humor
- say "bro" naturally when it fits
- emojis only when they hit perfect (🤣 💸 🇫🇷)
- no corporate bullshit, no linkedin energy
- french pride when relevant

examples of YOUR actual replies:
- "and FOMO for sure"
- "study comp sci" (to "fastest way to go broke")
- "true"
- "french 🇫🇷"
- "PRO but 💸"
- "nice try boss 🤣"
- "how can you explain her it's the best feeling ever"
- "a cracked engineer learning marketing is so gold bro it's not even close"
- "they just accepted that they won't train a model"
- "everyone is joking about google fumbling but the product is actually good"

---
TWEET TO REPLY TO:
@{tweet.author_handle}: {tweet.content}
---

reply type: {reply_type}
{REPLY_TYPE_INSTRUCTIONS[reply_type]}

RULES:
- BE SHORT. like actually short. 5-15 words ideal.
- lowercase
- no hashtags, no links
- don't start with "I agree" or "this is"
- sound like a 19yo dev who's building cool shit, not a marketer
- if you can say it in 3 words, do it
- emojis ONLY if they absolutely slap

just write the reply, nothing else. no quotes."""

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

"""Reply generation using LLM with viral prompt framework."""

import logging
import random

from twitter_bot.browser.watcher import ScrapedTweet
from twitter_bot.generation.provider import LLMProvider
from twitter_bot.state.manager import StateManager

logger = logging.getLogger(__name__)

# Non-English language indicators for filtering out non-English tweets
# We only want to reply to English tweets
NON_ENGLISH_INDICATORS = [
    # French
    'mec', 'mdr', 'ptdr', 'ptn', 'trop', "c'est", "j'ai", 'vraiment',
    'quoi', 'comme', 'très', 'alors', 'mais', 'putain', 'grave', 'tkt',
    'merci', 'bonjour', 'salut', 'pourquoi', 'parce', 'avoir', 'être',
    # Spanish
    'está', 'qué', 'esto', 'porque', 'también', 'gracias', 'hola',
    # German
    'nicht', 'auch', 'sind', 'wenn', 'haben', 'werden',
    # Portuguese
    'você', 'não', 'isso', 'também', 'porque', 'obrigado',
]

# Available reply types for rotation
# DATA-DRIVEN: Added types based on top-performing replies from analytics
REPLY_TYPES = [
    "hype_reaction",  # Excitement about news/releases (2287 impressions top)
    "contrarian",     # Challenge or skeptical take (1841 impressions top)
    "witty",          # Quick joke/observation
    "question",       # Follow-up question (triggers engagement)
    "one_liner",      # Minimal 2-5 words
    "hot_take",       # Spicy opinion
    "value_add",      # Share perspective/experience
]

# Instructions for each reply type - DATA-DRIVEN examples from top performers
REPLY_TYPE_INSTRUCTIONS = {
    "hype_reaction": """Express genuine excitement about news/announcement.
Examples from YOUR top tweets:
- "this is huge omg did they release their newest model yet ?" (2287 impressions)
- "holy game changer" (40 impressions)
- "they fixed claude code in opencode ??" (300 impressions)
Add a question or your quick take. Sound genuinely excited, not fake.""",

    "contrarian": """Challenge the post or offer a skeptical angle.
Examples from YOUR top tweets:
- "it's not vibe coding atp bro" (1841 impressions)
- "until you hit the weekly limit" (579 impressions)
- "still get absolutely cooked by claude code" (375 impressions)
- "everyone is joking about google fumbling but the product is actually good" (234 impressions)
Be real, not mean. Skepticism > blind agreement.""",

    "witty": """Quick joke, clever observation, dry humor.
Examples from YOUR top tweets:
- "holy nerd" (777 impressions)
- "HTML fr" (804 impressions)
- "meetings are the real tech debt" (8 impressions)
Keep it SHORT. Dry humor > try-hard funny.""",

    "question": """Ask a follow-up question that extends the conversation.
Examples from YOUR top tweets:
- "this is huge omg did they release their newest model yet ?" (2287 impressions)
- "they fixed claude code in opencode ??" (300 impressions)
Genuine curiosity > rhetorical questions.""",

    "one_liner": """Minimal response - 2-5 words max.
Examples from YOUR top tweets:
- "facts" (369 impressions)
- "true" (varies)
- "exactly"
- "holy nerd" (777 impressions)
Sometimes less is more.""",

    "hot_take": """Drop a spicy but genuine opinion.
Examples from YOUR top tweets:
- "don't use AI" (answering a how-to question ironically)
- "startup is gold when being a junior" (82 impressions)
Direct, slightly provocative, but not mean.""",

    "value_add": """Share relevant experience or perspective.
Examples from YOUR top tweets:
- "I mean, you still need to add some additional value to AI's power because if you don't, you'll just get replaced" (879 impressions)
- "really good model for design great integration too" (20 impressions)
Add genuine insight, not braggy flex.""",
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

    def is_english_tweet(self, tweet: ScrapedTweet) -> bool:
        """Check if a tweet is in English.

        Args:
            tweet: The tweet to check

        Returns:
            True if the tweet appears to be in English
        """
        content_lower = tweet.content.lower()
        non_english_matches = sum(
            1 for word in NON_ENGLISH_INDICATORS
            if f' {word} ' in f' {content_lower} ' or content_lower.startswith(f'{word} ')
        )
        # If 2+ non-English indicators found, it's likely not English
        return non_english_matches < 2

    def generate_reply(self, tweet: ScrapedTweet) -> tuple[str, str] | tuple[None, None]:
        """Generate a reply for a tweet.

        Args:
            tweet: The tweet to reply to

        Returns:
            Tuple of (reply_text, reply_type) or (None, None) if tweet should be skipped
        """
        # Skip non-English tweets
        if not self.is_english_tweet(tweet):
            logger.info(f"Skipping non-English tweet from @{tweet.author_handle}")
            return None, None

        # Get next reply type from rotation
        reply_type = self.state.get_next_reply_type()

        # Build the prompt
        prompt = self._build_prompt(tweet, reply_type)

        # Generate reply with higher token limit to ensure complete sentences
        logger.debug(f"Generating {reply_type} reply for tweet {tweet.tweet_id}")
        result = self.provider.generate(prompt, max_tokens=200)

        # Clean up the reply
        reply = self._clean_reply(result.text)

        # Check for incomplete sentences and regenerate if needed
        if self._is_incomplete(reply):
            logger.warning(f"Reply appears incomplete: '{reply}', regenerating...")
            # Try once more with explicit completion instruction
            result = self.provider.generate(prompt + "\n\nIMPORTANT: Write a COMPLETE sentence.", max_tokens=200)
            reply = self._clean_reply(result.text)

            # If still incomplete, skip this tweet
            if self._is_incomplete(reply):
                logger.warning(f"Reply still incomplete after retry, skipping")
                return None, None

        # Validate length
        if len(reply) > 280:
            logger.warning(f"Reply too long ({len(reply)} chars), truncating")
            reply = reply[:277] + "..."

        logger.info(f"Generated {reply_type} reply: {reply[:50]}...")
        return reply, reply_type

    def _is_incomplete(self, text: str) -> bool:
        """Check if a reply appears to be cut off mid-sentence.

        Args:
            text: The reply text to check

        Returns:
            True if the reply appears incomplete
        """
        if not text or len(text) < 3:
            return True

        text = text.strip()

        # Check for obvious truncation patterns
        truncation_indicators = [
            text.endswith('-'),
            text.endswith('...') and len(text) < 15,  # Very short with ellipsis
            text.endswith(' the'),
            text.endswith(' a'),
            text.endswith(' an'),
            text.endswith(' to'),
            text.endswith(' is'),
            text.endswith(' are'),
            text.endswith(' was'),
            text.endswith(' were'),
            text.endswith(' have'),
            text.endswith(' has'),
            text.endswith(' will'),
            text.endswith(' would'),
            text.endswith(' could'),
            text.endswith(' should'),
            text.endswith(' can'),
            text.endswith(' and'),
            text.endswith(' but'),
            text.endswith(' or'),
            text.endswith(' of'),
            text.endswith(' in'),
            text.endswith(' on'),
            text.endswith(' at'),
            text.endswith(' for'),
            text.endswith(' with'),
            text.endswith(' by'),
            text.endswith(' that'),
            text.endswith(' this'),
            text.endswith(' it'),
            text.endswith(" i"),
            text.endswith(" i'"),
            text.endswith(" you"),
            text.endswith(" they"),
            text.endswith(" we"),
        ]

        return any(truncation_indicators)

    def _build_prompt(self, tweet: ScrapedTweet, reply_type: str) -> str:
        """Build the reply generation prompt.

        Args:
            tweet: The tweet to reply to
            reply_type: The type of reply to generate

        Returns:
            Complete prompt string
        """
        return f"""you're maxime. 19yo dev from bordeaux. you build stuff with AI, next.js, typescript.

## YOUR TOP-PERFORMING REPLY PATTERNS (from your actual data):

**HYPE REACTIONS** (when news/releases drop):
- "this is huge omg did they release their newest model yet ?" → 2287 impressions
- "they fixed claude code in opencode ??" → 300 impressions

**CONTRARIAN/SKEPTIC** (challenge assumptions):
- "it's not vibe coding atp bro" → 1841 impressions
- "until you hit the weekly limit" → 579 impressions
- "everyone is joking about google fumbling but the product is actually good" → 234 impressions

**DRY HUMOR** (quick wit):
- "holy nerd" → 777 impressions
- "HTML fr" → 804 impressions (calling HTML a programming language)
- "meetings are the real tech debt"

**VALUE ADD** (genuine perspective):
- "I mean, you still need to add some additional value to AI's power..." → 879 impressions

---
TWEET TO REPLY TO:
@{tweet.author_handle}: {tweet.content}
---

reply type: {reply_type}
{REPLY_TYPE_INSTRUCTIONS.get(reply_type, REPLY_TYPE_INSTRUCTIONS["witty"])}

RULES:
- ALWAYS REPLY IN ENGLISH
- ALWAYS write complete sentences - never cut off mid-thought
- BE SHORT but COMPLETE. 5-20 words ideal, but finish your thought.
- lowercase always
- no hashtags, no links
- sound natural, like texting a dev friend
- emojis: RARELY (1 in 10 replies max, only 🤣 💸 😭 🤯)
- contrarian > generic agreement
- questions extend conversations
- dry humor > try-hard jokes

OUTPUT: just the reply text, nothing else. Make sure it's a COMPLETE thought."""

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

"""Reply generation using LLM with viral prompt framework."""

import logging
import random

from twitter_bot.browser.watcher import ScrapedTweet
from twitter_bot.generation.provider import LLMProvider
from twitter_bot.state.manager import StateManager

logger = logging.getLogger(__name__)

# French language indicators for detecting French tweets
# Used to trigger French replies which perform 2-3x better on French accounts
FRENCH_INDICATORS = [
    'mec', 'mdr', 'ptdr', 'ptn', 'trop', "c'est", "j'ai", 'vraiment',
    'quoi', 'comme', 'très', 'alors', 'mais', 'putain', 'grave', 'tkt'
]

# Available reply types for rotation
# DATA-DRIVEN: Added types based on top-performing replies from analytics
REPLY_TYPES = [
    "hype_reaction",  # NEW: Excitement about news/releases (2287 impressions top)
    "contrarian",     # NEW: Challenge or skeptical take (1841 impressions top)
    "witty",          # Quick joke/observation
    "question",       # NEW: Follow-up question (triggers engagement)
    "one_liner",      # Minimal 2-5 words
    "hot_take",       # Spicy opinion
    "value_add",      # Share perspective/experience (renamed from flex)
    "french",         # NEW: French reply for French accounts (2847 impressions top)
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

    "french": """Reply in French for French-speaking accounts.
Examples from YOUR top tweets:
- "mon rêve j'ai trop hâte" (2847 impressions!)
- "ptn mec linkedin s'y met aussi c'est terrible" (422 impressions)
- "la phrase commençait bien comment t'as tout whippin par pitié" (504 impressions)
Use natural French slang (mec, ptn, mdr). Short and punchy.""",
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
        # Detect French tweets - prioritize French replies (they perform 2-3x better)
        # Require 2+ matches to avoid false positives (e.g., "non" in "non-blocking")
        content_lower = tweet.content.lower()
        french_matches = sum(1 for word in FRENCH_INDICATORS if word in content_lower)
        is_french_tweet = french_matches >= 2

        if is_french_tweet:
            # 70% chance to reply in French for French tweets (high performance)
            if random.random() < 0.7:
                reply_type = "french"
                logger.info(f"Detected French tweet, using French reply type")
            else:
                reply_type = self.state.get_next_reply_type()
        else:
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
        # Detect if this might be a French tweet/account (2+ matches required)
        content_lower = tweet.content.lower()
        french_matches = sum(1 for word in FRENCH_INDICATORS if word in content_lower)
        is_french_tweet = french_matches >= 2

        # Adjust instructions for French tweets
        language_note = ""
        if is_french_tweet and reply_type != "french":
            language_note = "\n**NOTE: This tweet is in French. Consider replying in French if natural.**"
        elif reply_type == "french":
            language_note = "\n**REPLY IN FRENCH. Use natural slang (mec, ptn, mdr). Short and punchy.**"

        return f"""you're maxime. 19yo french dev from bordeaux. you build stuff with AI, next.js, typescript.

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

**FRENCH** (for French accounts - VERY high engagement):
- "mon rêve j'ai trop hâte" → 2847 impressions
- "ptn mec linkedin s'y met aussi c'est terrible" → 422 impressions

**VALUE ADD** (genuine perspective):
- "I mean, you still need to add some additional value to AI's power..." → 879 impressions

---
TWEET TO REPLY TO:
@{tweet.author_handle}: {tweet.content}
---

reply type: {reply_type}
{REPLY_TYPE_INSTRUCTIONS.get(reply_type, REPLY_TYPE_INSTRUCTIONS["witty"])}
{language_note}

RULES:
- BE SHORT. 5-20 words ideal. 2-5 words often best.
- lowercase always
- no hashtags, no links
- sound natural, like texting a dev friend
- emojis: RARELY (1 in 10 replies max, only 🤣 💸 🇫🇷 😭 🤯)
- contrarian > generic agreement
- questions extend conversations
- dry humor > try-hard jokes

OUTPUT: just the reply text, nothing else."""

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

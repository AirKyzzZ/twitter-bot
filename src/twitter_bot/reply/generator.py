"""Reply generation using LLM with viral prompt framework."""

import logging
import random

from twitter_bot.browser.watcher import ScrapedTweet
from twitter_bot.generation.provider import LLMProvider
from twitter_bot.state.manager import StateManager

logger = logging.getLogger(__name__)

# Non-English language indicators for filtering out non-English tweets
# We only want to reply to English tweets
# These are common words that strongly indicate non-English content
NON_ENGLISH_INDICATORS = [
    # French - common words and phrases
    'mec', 'mdr', 'ptdr', 'ptn', 'trop', "c'est", "j'ai", 'vraiment',
    'quoi', 'très', 'alors', 'putain', 'grave', 'tkt', 'cette',
    'merci', 'bonjour', 'salut', 'pourquoi', 'parce', 'avoir', 'être',
    'les ', 'des ', 'une ', 'pour ', 'avec ', 'dans ', 'sur ', 'qui ',
    'que ', 'est ', 'sont ', 'ont ', 'pas ', 'plus ', 'fait ',
    'entre', 'même', 'aussi', 'tout', 'bien', 'gens', 'faire',
    'peut', 'deux', 'leur', 'notre', 'votre', 'cette', 'celui',
    'après', 'avant', 'encore', 'toujours', 'jamais', 'rien',
    'fermes', 'années', 'heure', 'problème', 'gauche', 'droite',
    'utilise', 'argent', 'gagne', 'plupart', 'audace', 'approbation',
    'résume', 'parfaitement', 'automatiser', 'colmater', 'fuites',
    'natalité', 'europe', 'chine', 'diffusions', 'simultanées',
    'rapportent', 'appareil', 'installations', 'publicité', 'produits',
    # Spanish
    'está', 'qué', 'esto', 'porque', 'también', 'gracias', 'hola',
    'para', 'como', 'pero', 'más', 'este', 'cuando', 'todo',
    # German
    'nicht', 'auch', 'sind', 'wenn', 'haben', 'werden', 'diese',
    'kann', 'wird', 'gibt', 'nach', 'noch', 'über', 'sein',
    # Portuguese
    'você', 'não', 'isso', 'também', 'porque', 'obrigado',
    'para', 'como', 'mais', 'esse', 'esta', 'pela', 'pelo',
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

        # Simple substring matching - if the word appears anywhere, count it
        non_english_matches = sum(
            1 for word in NON_ENGLISH_INDICATORS
            if word in content_lower
        )

        # If 2+ non-English indicators found, it's likely not English
        if non_english_matches >= 2:
            logger.debug(f"Detected {non_english_matches} non-English indicators in tweet")
            return False

        return True

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
        text_lower = text.lower()

        # Words/patterns that indicate incomplete sentences
        incomplete_endings = [
            # Articles and determiners
            ' the', ' a', ' an', ' this', ' that', ' these', ' those',
            # Prepositions
            ' to', ' of', ' in', ' on', ' at', ' for', ' with', ' by',
            ' from', ' into', ' about', ' through', ' during', ' before',
            ' after', ' above', ' below', ' between', ' under', ' over',
            # Conjunctions
            ' and', ' but', ' or', ' nor', ' so', ' yet', ' because',
            ' although', ' while', ' if', ' when', ' where', ' how',
            # Verbs (auxiliary/modal)
            ' is', ' are', ' was', ' were', ' be', ' been', ' being',
            ' have', ' has', ' had', ' do', ' does', ' did',
            ' will', ' would', ' could', ' should', ' can', ' may', ' might',
            ' must', ' shall',
            # Pronouns
            ' i', ' you', ' he', ' she', ' it', ' we', ' they',
            ' my', ' your', ' his', ' her', ' its', ' our', ' their',
            # Adverbs that expect continuation
            ' really', ' very', ' just', ' only', ' even', ' still',
            ' already', ' always', ' never', ' often', ' sometimes',
            ' definitely', ' probably', ' maybe', ' perhaps',
            ' actually', ' basically', ' literally', ' honestly',
            ' pretty', ' quite', ' rather', ' somewhat',
            # Question words mid-sentence
            ' what', ' why', ' who', ' which', ' whose',
            # Other incomplete patterns
            " i'", " it'", " that'", " what'", " who'",
            ' not', ' no', ' so', ' as', ' like', ' than',
        ]

        # Check for endings that indicate truncation
        for ending in incomplete_endings:
            if text_lower.endswith(ending):
                return True

        # Check for cut-off mid-word (ends with hyphen or partial word)
        if text.endswith('-'):
            return True

        # Check for very short ellipsis
        if text.endswith('...') and len(text) < 20:
            return True

        # Check if last word looks truncated (very short, no vowels, etc.)
        words = text.split()
        if words:
            last_word = words[-1].rstrip('.,!?;:').lower()

            # Valid short words that are complete
            valid_short_words = {
                'i', 'a', 'ok', 'no', 'go', 'do', 'so', 'up', 'it', 'is', 'as', 'at',
                'be', 'by', 'he', 'if', 'in', 'me', 'my', 'of', 'on', 'or', 'to', 'us',
                'we', 'an', 'am', 'oh', 'hi', 'yo', 'lol', 'omg', 'wow', 'yes', 'yep',
                'nah', 'nope', 'too', 'now', 'new', 'old', 'big', 'bad', 'hot', 'top',
                'low', 'out', 'off', 'own', 'way', 'day', 'guy', 'man', 'got', 'get',
                'let', 'set', 'put', 'run', 'try', 'use', 'see', 'say', 'ask', 'add',
                'end', 'win', 'ago', 'due', 'via', 'per', 'pro', 'con', 'dev', 'api',
                'app', 'web', 'css', 'sql', 'llm', 'gpu', 'cpu', 'ram', 'ssd', 'hdd',
            }

            # If last word is 1-3 chars and not a valid short word, likely truncated
            if len(last_word) <= 3 and last_word not in valid_short_words:
                return True

            # Adverbs ending in -ly that usually expect continuation
            incomplete_adverbs = [
                'definitely', 'probably', 'basically', 'literally', 'honestly',
                'actually', 'really', 'mostly', 'nearly', 'hardly', 'barely',
                'only', 'just', 'early', 'lately', 'recently', 'currently',
                'previously', 'finally', 'initially', 'especially', 'particularly',
            ]
            if last_word in incomplete_adverbs:
                return True

            # Check for word fragments that look cut off (no vowels = likely truncated)
            if len(last_word) <= 4 and not any(c in last_word for c in 'aeiou'):
                return True

        return False

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

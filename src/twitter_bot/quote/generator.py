"""Generate quote tweets in Maxime's voice.

DATA-DRIVEN: Quote tweets get 3.7% engagement vs 1.8% for standard tweets.
Key: Add genuine value/perspective, don't just react.
"""

import logging
import random
from dataclasses import dataclass

from twitter_bot.generation.provider import LLMProvider
from twitter_bot.quote.finder import TrendingTweet

logger = logging.getLogger(__name__)


@dataclass
class QuoteTweetDraft:
    """A generated quote tweet draft."""
    
    content: str
    original_tweet: TrendingTweet
    quote_type: str  # "hot_take", "agree_extend", "counter", "humor"
    
    @property
    def full_text(self) -> str:
        """Full text that would appear (content + quoted tweet link)."""
        return f"{self.content}\n\n{self.original_tweet.url}"


QUOTE_TYPES = [
    "hot_take",      # Bold opinion building on their point
    "agree_extend",  # Agree and add your angle
    "counter",       # Respectful disagreement with reasoning
    "humor",         # Witty observation about their take
    "experience",    # Share relevant personal experience
]


class QuoteTweetGenerator:
    """Generate quote tweets in Maxime's voice."""

    def __init__(
        self,
        provider: LLMProvider,
        voice_profile: str = "",
    ):
        self.provider = provider
        self.voice_profile = voice_profile

    def _build_prompt(
        self,
        tweet: TrendingTweet,
        quote_type: str | None = None,
    ) -> str:
        """Build the generation prompt for a quote tweet."""
        
        if quote_type is None:
            quote_type = random.choice(QUOTE_TYPES)
        
        prompt_parts = []
        
        # Voice profile
        if self.voice_profile:
            prompt_parts.append(f"""## Voice Profile
{self.voice_profile}
""")
        
        # Context
        prompt_parts.append(f"""## YOUR TASK: Quote Tweet

You're Maxime (19, Bordeaux dev, builds Verana/2060.io/Klyx). 
Generate a QUOTE TWEET response to this viral tweet.

## ORIGINAL TWEET
@{tweet.author_handle} ({tweet.author_followers:,} followers):
"{tweet.content}"

Engagement: {tweet.likes:,} likes, {tweet.retweets:,} RTs

## QUOTE TYPE: {quote_type.upper()}

{self._get_type_instructions(quote_type)}

## RULES

1. **MAX 100 CHARACTERS** - Short punchy quotes perform best
2. **Add genuine value** - Don't just say "this" or "so true"
3. **Your perspective matters** - What unique angle can you add?
4. **Be authentic** - 19yo dev vibes, not LinkedIn energy
5. **No hashtags, ever**
6. **Lowercase always**

## BANNED PATTERNS
- "This." / "So true" / "Exactly"
- "Couldn't agree more"
- Any generic agreement
- "This is why..." 
- "@username is right because..."
- Starting with "I"

## OUTPUT

Return ONLY the quote tweet text (under 100 chars).
No quotes. No explanation. No meta-commentary.
The quoted tweet URL will be added automatically.
""")
        
        return "\n".join(prompt_parts)

    def _get_type_instructions(self, quote_type: str) -> str:
        """Get specific instructions for each quote type."""
        instructions = {
            "hot_take": """
**HOT TAKE**: Build on their point with a spicier angle.
- Take their idea further
- Make a bolder claim
- Add controversy (respectfully)
Example: Original: "AI will change coding" → Your quote: "it already has. half my code is claude's now"
""",
            "agree_extend": """
**AGREE & EXTEND**: Add your unique experience/insight.
- Validate with real experience
- Add a specific example
- Extend to a related insight
Example: Original: "TypeScript saves debugging time" → Your quote: "caught 3 prod bugs in my last PR review just from types"
""",
            "counter": """
**COUNTER**: Respectfully disagree with reasoning.
- Challenge one specific point
- Offer alternative view
- Keep it civil but firm
Example: Original: "Microservices > monoliths" → Your quote: "depends. my monolith deploys in 30 seconds"
""",
            "humor": """
**HUMOR**: Make a witty observation about their take.
- Dry humor preferred
- Self-deprecating works
- Ironic observations
Example: Original: "Learn to code in 30 days" → Your quote: "day 31: realizes i know nothing"
""",
            "experience": """
**EXPERIENCE**: Share a relevant personal story (brief).
- Real anecdote
- Specific details
- Connect to their point
Example: Original: "Ship fast, iterate" → Your quote: "shipped my side project at 3am, woke up to 50 signups"
""",
        }
        return instructions.get(quote_type, instructions["hot_take"])

    def generate_quote(
        self,
        tweet: TrendingTweet,
        quote_type: str | None = None,
    ) -> QuoteTweetDraft | None:
        """Generate a quote tweet for a trending tweet.
        
        Args:
            tweet: The tweet to quote
            quote_type: Type of quote (random if None)
            
        Returns:
            QuoteTweetDraft or None if generation fails
        """
        if quote_type is None:
            quote_type = random.choice(QUOTE_TYPES)
        
        prompt = self._build_prompt(tweet, quote_type)
        
        try:
            results = self.provider.generate_multiple(prompt, n=1, max_tokens=150)
            
            if not results:
                logger.warning("No results from LLM")
                return None
            
            content = results[0].text.strip()
            
            # Clean up
            if content.startswith('"') and content.endswith('"'):
                content = content[1:-1]
            
            # Enforce length limit
            if len(content) > 140:
                # Try to truncate at sentence boundary
                if ". " in content[:140]:
                    content = content[:content.rfind(". ", 0, 140) + 1]
                else:
                    content = content[:140].rsplit(" ", 1)[0]
            
            # Remove trailing punctuation for cleaner look
            content = content.rstrip(".,")
            
            return QuoteTweetDraft(
                content=content,
                original_tweet=tweet,
                quote_type=quote_type,
            )
            
        except Exception as e:
            logger.error(f"Quote generation failed: {e}")
            return None

    def generate_multiple(
        self,
        tweet: TrendingTweet,
        n: int = 3,
    ) -> list[QuoteTweetDraft]:
        """Generate multiple quote tweet options.
        
        Args:
            tweet: The tweet to quote
            n: Number of drafts to generate
            
        Returns:
            List of QuoteTweetDraft objects
        """
        drafts = []
        types_used = set()
        
        for _ in range(n):
            # Try to use different quote types
            available_types = [t for t in QUOTE_TYPES if t not in types_used]
            if not available_types:
                available_types = QUOTE_TYPES
            
            quote_type = random.choice(available_types)
            types_used.add(quote_type)
            
            draft = self.generate_quote(tweet, quote_type)
            if draft:
                drafts.append(draft)
        
        return drafts

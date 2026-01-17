---
title: 'Hybrid Reply Bot'
slug: 'hybrid-reply-bot'
created: '2026-01-17'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - Python 3.11+
  - Playwright (browser automation)
  - playwright-stealth (anti-detection)
  - Typer (CLI framework)
  - Pydantic Settings (configuration)
  - httpx (HTTP client)
  - tenacity (retry logic)
  - Groq/OpenAI/Gemini (LLM providers)
files_to_modify:
  - src/twitter_bot/config.py
  - src/twitter_bot/twitter/client.py
  - src/twitter_bot/state/manager.py
  - src/twitter_bot/cli.py
  - config.yaml
files_to_create:
  - src/twitter_bot/browser/__init__.py
  - src/twitter_bot/browser/stealth.py
  - src/twitter_bot/browser/watcher.py
  - src/twitter_bot/reply/__init__.py
  - src/twitter_bot/reply/scorer.py
  - src/twitter_bot/reply/generator.py
  - tests/reply/test_scorer.py
  - tests/reply/test_generator.py
code_patterns:
  - Pydantic Settings for config with env var interpolation
  - Thin abstraction layer for external services
  - tenacity decorators for retry logic
  - Typer with Rich for CLI
  - JSON state persistence in StateManager
  - Domain-based module organization
  - Async event loop for real-time watching
---

# Tech-Spec: Hybrid Reply Bot (Local-First)

**Created:** 2026-01-17
**Status:** Ready for Development
**Execution:** Local Mac (M1) - NOT GitHub Actions

## Overview

### Problem Statement

Maxime has a small Twitter account and manually replying to trending/high-engagement tweets in his niche is time-consuming but highly effective for growth. Replies offer higher leverage for small accounts because:
- You piggyback on existing engagement/visibility
- Context makes quality replies easier to generate
- Strategic replies drive profile visits and follows
- 67% of account growth is tied to reply consistency

### Solution

**Local-first hybrid architecture:**

1. **Poster Bot:** Stays on GitHub Actions (10 single tweets/day)

2. **Reply Bot (NEW - Local):**
   - Runs on local Mac as a daemon
   - Browser watches timeline in real-time
   - Scores incoming tweets for reply potential
   - Generates viral replies using LLM with optimized prompts
   - Posts replies via Twitter API (safe, legitimate)

### Why Local Instead of GitHub Actions

| Concern | GHA Problem | Local Solution |
|---------|-------------|----------------|
| **2FA/Login** | Can't handle interactively | Login once manually, session persists |
| **Session persistence** | Complex cookie management | Browser stays open or local cookie storage |
| **Detection risk** | Datacenter IPs flagged | Residential IP, natural browsing pattern |
| **Debugging** | Hard to see what's happening | Watch it run, see errors in real-time |
| **Rate limiting** | Cron-based, inflexible | Real-time adaptive control |

### Scope

**In Scope:**
- Poster bot config change (disable threads, cap at 10/day)
- New `browser/` module with Playwright for local use
- Real-time timeline watcher
- Tweet scoring system (topics, engagement, freshness, author size)
- **Viral reply prompt engineering** (main focus)
- Extend TwitterClient with `post_reply()` method
- Extend StateManager with replied tweets tracking
- New CLI commands: `reply-watch`, `reply-once`, `reply-status`
- Local daemon mode with graceful shutdown

**Out of Scope:**
- GitHub Actions for reply bot (poster stays on GHA)
- Search/explore page scraping (timeline only)
- Multi-account support
- Media/image replies
- Thread replies

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Local Mac (M1)                               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Playwright Browser (Chromium)                            │   │
│  │  - Logged into Twitter (manual first login)               │   │
│  │  - Session persists via local cookies                     │   │
│  │  - Human-like behavior (delays, scrolling)                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Timeline Watcher (async loop)                            │   │
│  │  - Polls timeline every 30-60 seconds                     │   │
│  │  - Extracts new tweets since last check                   │   │
│  │  - Parses: content, author, engagement metrics            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Tweet Scorer                                             │   │
│  │  - Topic relevance (keyword + semantic)                   │   │
│  │  - Engagement velocity                                    │   │
│  │  - Author follower range (5K-100K sweet spot)             │   │
│  │  - Recency (< 1 hour preferred)                           │   │
│  │  - Not already replied                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Reply Generator (LLM)                                    │   │
│  │  - Viral reply prompt framework                           │   │
│  │  - 5 reply types with rotation                            │   │
│  │  - Maxime's voice profile                                 │   │
│  │  - Brevity constraint (< 200 chars ideal)                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Twitter API (post_reply)                                 │   │
│  │  - Safe, legitimate API posting                           │   │
│  │  - Rate limited (40/day budget)                           │   │
│  │  - Retry with exponential backoff                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  State Manager                                            │   │
│  │  - Track replied tweets (prevent duplicates)              │   │
│  │  - Daily reply count                                      │   │
│  │  - Reply type rotation history                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **StealthBrowser** | Launch Chromium with stealth patches, manage session |
| **TimelineWatcher** | Poll timeline, extract tweets, detect new content |
| **TweetScorer** | Score and rank tweets for reply potential |
| **ReplyGenerator** | Generate viral replies using LLM |
| **TwitterClient** | Post replies via API |
| **StateManager** | Track state, prevent duplicates, count daily replies |
| **CLI** | Commands: `reply-watch`, `reply-once`, `reply-status` |

## Viral Reply Strategy (Core Focus)

### Research-Based Insights

**What makes replies go viral:**
- First 15 minutes after original tweet is critical window
- Replies under viral tweets with momentum get seen
- Add value - not just "Great post!" (that's spam)
- Questions drive engagement
- Contrarian takes (respectful) spark discussion
- Personal anecdotes create connection
- Brevity wins (< 200 chars ideal)

### Reply Types (Rotate for Variety)

| Type | Pattern | Example |
|------|---------|---------|
| **Expert Add-On** | "This + [insight from experience]" | "This. Also found that X works even better when you Y." |
| **Contrarian Nudge** | "Mostly agree, but [counterpoint]" | "Solid take. Though I'd push back on Z - in my exp..." |
| **Curious Question** | "Have you tried [X]?" | "Curious - did you consider using X instead? Found it faster for Y." |
| **Micro-Story** | Brief personal anecdote | "Learned this the hard way. Spent 3 days on X before realizing..." |
| **Simplifier** | Reframe more memorably | "TL;DR: [their point in 10 words]" |

### Master Reply Prompt

```markdown
## CONTEXT
You are Maxime. 19. Bordeaux. Builder.

You're replying to this tweet:
---
@{{author_handle}} ({{author_followers}} followers):
"{{tweet_content}}"
---
Engagement: {{likes}} likes, {{retweets}} RTs, {{replies}} replies

## YOUR MISSION
Write a reply that:
1. ADDS VALUE - Not "Great take!" but actual insight
2. STOPS THE SCROLL - First words must hook
3. SOUNDS LIKE YOU - Builder, direct, no corporate speak
4. DRIVES ENGAGEMENT - Makes people want to reply to YOU

## REPLY TYPE FOR THIS ONE: {{reply_type}}

{{reply_type_specific_instructions}}

## CONSTRAINTS
- MAX 200 characters (punchy wins)
- No hashtags ever
- No links (algorithmic penalty)
- No emojis unless absolutely natural
- No "I agree" or "This is so true"
- Sound like a 19-year-old builder, not a LinkedIn influencer

## BANNED PHRASES
- "Great post!", "Love this!", "So true!"
- "Game changer", "Level up", "Unlock"
- "This is the way", "Couldn't agree more"
- Starting with "I"
- Generic praise without substance

## YOUR ANGLE
Connect to YOUR expertise when relevant:
- AI/ML, LLMs, Claude, GPT
- Next.js, TypeScript, React, Python
- Self-Sovereign Identity, DIDs, Verifiable Credentials
- Indie hacking, shipping, building in public
- Parkour (discipline, risk, commitment)

## OUTPUT
Reply text only. No quotes. No explanation.
```

### Reply Type Specific Instructions

**Expert Add-On:**
```
Add ONE specific insight from your experience that extends their point.
Pattern: "[Agreement/validation] + [Your specific addition]"
Must include concrete detail (numbers, specific tech, real example).
```

**Contrarian Nudge:**
```
Respectfully push back on ONE aspect while acknowledging the core point.
Pattern: "[Acknowledge merit] + but [your counterpoint] + [brief why]"
Not argumentative - thoughtful disagreement that sparks discussion.
```

**Curious Question:**
```
Ask ONE specific question that shows you understood AND thought deeper.
Pattern: "[Brief context] + [Specific question]?"
The question should make THEM think, not be easily answered.
```

**Micro-Story:**
```
Share a 1-2 sentence personal experience that relates.
Pattern: "[What happened] + [What you learned]"
Must be specific (not "I once had this problem too").
```

**Simplifier:**
```
Reframe their point more memorably in fewer words.
Pattern: "TL;DR: [their point distilled]" or "[Metaphor that captures it]"
Add a fresh angle they might not have considered.
```

## Implementation Plan

### Tasks

#### Phase 1: Foundation (Tasks 1-5)

- [ ] **Task 1: Add Playwright dependencies**
  - File: `pyproject.toml`
  - Action: Add `playwright>=1.40.0` and `playwright-stealth>=1.0.0`
  - Run: `uv add playwright playwright-stealth && playwright install chromium`

- [ ] **Task 2: Add configuration models**
  - File: `src/twitter_bot/config.py`
  - Action: Create config models
  ```python
  class ReplyConfig(BaseModel):
      enabled: bool = True
      max_per_day: int = 40
      min_delay_seconds: int = 120  # 2 min between replies
      max_delay_seconds: int = 300  # 5 min max
      target_min_followers: int = 1000
      target_max_followers: int = 500000
      min_engagement_score: int = 5
      score_threshold: float = 0.6  # Min score to consider replying
      watch_interval_seconds: int = 45  # How often to check timeline
      topics: list[str] = Field(default_factory=list)  # Override boost_topics
      cookies_path: str = "~/.twitter-bot/cookies.json"

  class PosterConfig(BaseModel):
      max_per_day: int = 10
      allow_threads: bool = False
  ```

- [ ] **Task 3: Update config.yaml**
  - File: `config.yaml`
  - Action: Add `reply:` and `poster:` sections

- [ ] **Task 4: Extend StateManager**
  - File: `src/twitter_bot/state/manager.py`
  - Action: Add reply tracking
  ```python
  @dataclass
  class RepliedTweet:
      original_tweet_id: str
      original_author: str
      original_content: str
      reply_tweet_id: str
      reply_content: str
      reply_type: str  # expert, contrarian, question, story, simplifier
      replied_at: str

  # Add to State:
  replied_tweets: list[RepliedTweet] = field(default_factory=list)
  replied_tweet_ids: set[str] = field(default_factory=set)
  reply_type_history: list[str] = field(default_factory=list)  # Last N types
  last_reply_at: str | None = None

  # Add methods:
  def is_tweet_replied(self, tweet_id: str) -> bool
  def record_reply(self, replied: RepliedTweet) -> None
  def get_replies_today_count(self, timezone: str) -> int
  def get_next_reply_type(self) -> str  # Rotate through types
  def can_reply_now(self, min_delay: int) -> bool
  ```

- [ ] **Task 5: Add post_reply to TwitterClient**
  - File: `src/twitter_bot/twitter/client.py`
  - Action: Add reply method
  ```python
  @retry(
      stop=stop_after_attempt(3),
      wait=wait_exponential(multiplier=1, min=4, max=60),
      retry=retry_if_exception_type(TwitterAPIError),
  )
  def post_reply(self, text: str, in_reply_to_tweet_id: str) -> Tweet:
      """Post a reply to a tweet."""
      payload = {
          "text": text,
          "reply": {"in_reply_to_tweet_id": in_reply_to_tweet_id}
      }
      # ... existing post logic with payload
  ```

#### Phase 2: Browser Module (Tasks 6-8)

- [ ] **Task 6: Create browser module**
  - File: `src/twitter_bot/browser/__init__.py`
  - Action: Export `StealthBrowser`, `TimelineWatcher`, `ScrapedTweet`

- [ ] **Task 7: Implement StealthBrowser**
  - File: `src/twitter_bot/browser/stealth.py`
  ```python
  class StealthBrowser:
      """Manages Playwright browser with stealth patches."""

      def __init__(self, cookies_path: Path, headless: bool = False):
          self.cookies_path = cookies_path
          self.headless = headless
          self.browser: Browser | None = None
          self.context: BrowserContext | None = None
          self.page: Page | None = None

      async def __aenter__(self) -> "StealthBrowser":
          """Launch browser and restore session."""
          playwright = await async_playwright().start()
          self.browser = await playwright.chromium.launch(
              headless=self.headless,
              args=['--disable-blink-features=AutomationControlled']
          )
          self.context = await self.browser.new_context(
              viewport={'width': 1280, 'height': 800},
              user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...'
          )
          # Apply stealth patches
          await stealth_async(self.page)
          # Load cookies if exist
          if self.cookies_path.exists():
              cookies = json.loads(self.cookies_path.read_text())
              await self.context.add_cookies(cookies)
          self.page = await self.context.new_page()
          return self

      async def __aexit__(self, *args):
          """Save cookies and close browser."""
          if self.context:
              cookies = await self.context.cookies()
              self.cookies_path.parent.mkdir(parents=True, exist_ok=True)
              self.cookies_path.write_text(json.dumps(cookies))
          if self.browser:
              await self.browser.close()

      async def random_delay(self, min_s: float = 1, max_s: float = 3):
          """Human-like random delay."""
          await asyncio.sleep(random.uniform(min_s, max_s))

      async def ensure_logged_in(self) -> bool:
          """Check if logged in, prompt for manual login if not."""
          await self.page.goto('https://twitter.com/home')
          await self.random_delay(2, 4)
          # Check for login indicators
          if await self.page.query_selector('[data-testid="SideNav_NewTweet_Button"]'):
              return True
          print("Not logged in. Please log in manually in the browser window...")
          print("Press Enter when done.")
          input()
          return await self.ensure_logged_in()
  ```

- [ ] **Task 8: Implement TimelineWatcher**
  - File: `src/twitter_bot/browser/watcher.py`
  ```python
  @dataclass
  class ScrapedTweet:
      tweet_id: str
      author_handle: str
      author_name: str
      author_followers: int | None  # May not be available
      content: str
      likes: int
      retweets: int
      replies: int
      timestamp: datetime
      is_retweet: bool
      is_quote: bool
      scraped_at: datetime = field(default_factory=datetime.utcnow)

  class TimelineWatcher:
      """Watches timeline for new tweets."""

      def __init__(self, browser: StealthBrowser, state: StateManager):
          self.browser = browser
          self.state = state
          self.seen_tweet_ids: set[str] = set()

      async def scrape_visible_tweets(self) -> list[ScrapedTweet]:
          """Scrape currently visible tweets from timeline."""
          tweets = []
          # Use data-testid attributes (more stable than classes)
          tweet_elements = await self.browser.page.query_selector_all(
              '[data-testid="tweet"]'
          )
          for el in tweet_elements[:20]:  # Limit to 20 per scrape
              try:
                  tweet = await self._parse_tweet_element(el)
                  if tweet and tweet.tweet_id not in self.seen_tweet_ids:
                      tweets.append(tweet)
                      self.seen_tweet_ids.add(tweet.tweet_id)
              except Exception as e:
                  logging.warning(f"Failed to parse tweet: {e}")
          return tweets

      async def _parse_tweet_element(self, el) -> ScrapedTweet | None:
          """Parse a tweet element into ScrapedTweet."""
          # Extract tweet ID from link
          link = await el.query_selector('a[href*="/status/"]')
          if not link:
              return None
          href = await link.get_attribute('href')
          tweet_id = href.split('/status/')[-1].split('?')[0]

          # Extract author
          author_el = await el.query_selector('[data-testid="User-Name"]')
          author_handle = await self._extract_handle(author_el)
          author_name = await self._extract_name(author_el)

          # Extract content
          content_el = await el.query_selector('[data-testid="tweetText"]')
          content = await content_el.inner_text() if content_el else ""

          # Extract metrics (likes, RTs, replies)
          metrics = await self._extract_metrics(el)

          # Check if retweet/quote
          is_retweet = await el.query_selector('[data-testid="socialContext"]') is not None
          is_quote = await el.query_selector('[data-testid="quoteTweet"]') is not None

          return ScrapedTweet(
              tweet_id=tweet_id,
              author_handle=author_handle,
              author_name=author_name,
              author_followers=None,  # Would need profile visit
              content=content,
              likes=metrics.get('likes', 0),
              retweets=metrics.get('retweets', 0),
              replies=metrics.get('replies', 0),
              timestamp=datetime.utcnow(),  # Approximate
              is_retweet=is_retweet,
              is_quote=is_quote,
          )

      async def watch(
          self,
          interval: int = 45,
          on_new_tweets: Callable[[list[ScrapedTweet]], Awaitable[None]] = None
      ):
          """Watch timeline continuously, calling callback on new tweets."""
          await self.browser.page.goto('https://twitter.com/home')
          await self.browser.random_delay(2, 4)

          while True:
              try:
                  # Scroll down slightly to load more
                  await self.browser.page.evaluate('window.scrollBy(0, 300)')
                  await self.browser.random_delay(1, 2)

                  # Scrape visible tweets
                  new_tweets = await self.scrape_visible_tweets()

                  if new_tweets and on_new_tweets:
                      await on_new_tweets(new_tweets)

                  # Scroll back up
                  await self.browser.page.evaluate('window.scrollTo(0, 0)')
                  await self.browser.random_delay(1, 2)

                  # Refresh to get latest
                  await self.browser.page.reload()
                  await self.browser.random_delay(interval * 0.8, interval * 1.2)

              except Exception as e:
                  logging.error(f"Watch loop error: {e}")
                  await asyncio.sleep(30)  # Back off on error
  ```

#### Phase 3: Reply Logic (Tasks 9-11)

- [ ] **Task 9: Create reply module**
  - File: `src/twitter_bot/reply/__init__.py`
  - Export: `TweetScorer`, `ReplyGenerator`

- [ ] **Task 10: Implement TweetScorer**
  - File: `src/twitter_bot/reply/scorer.py`
  ```python
  class TweetScorer:
      """Scores tweets for reply potential."""

      def __init__(
          self,
          config: ReplyConfig,
          boost_topics: list[str],
          state: StateManager
      ):
          self.config = config
          self.topics = config.topics or boost_topics
          self.state = state

      def score(self, tweet: ScrapedTweet) -> float:
          """Score a tweet from 0.0 to 1.0."""
          if self.state.is_tweet_replied(tweet.tweet_id):
              return 0.0
          if tweet.is_retweet:
              return 0.0  # Don't reply to RTs

          scores = []

          # Topic relevance (0-1)
          topic_score = self._score_topic_relevance(tweet.content)
          scores.append(('topic', topic_score, 0.35))

          # Engagement (0-1) - normalize to reasonable range
          engagement = tweet.likes + tweet.retweets * 2 + tweet.replies * 3
          engagement_score = min(1.0, engagement / 100)  # 100+ = max
          scores.append(('engagement', engagement_score, 0.30))

          # Author size sweet spot (0-1)
          if tweet.author_followers:
              follower_score = self._score_follower_range(tweet.author_followers)
          else:
              follower_score = 0.5  # Unknown = neutral
          scores.append(('followers', follower_score, 0.20))

          # Recency bonus (0-1)
          # For now, all scraped tweets are "recent"
          recency_score = 0.8
          scores.append(('recency', recency_score, 0.15))

          # Weighted average
          total = sum(score * weight for _, score, weight in scores)
          return total

      def _score_topic_relevance(self, content: str) -> float:
          """Score topic relevance via keyword matching."""
          content_lower = content.lower()
          matches = sum(1 for topic in self.topics if topic.lower() in content_lower)
          if matches == 0:
              return 0.1  # Baseline for timeline relevance
          return min(1.0, 0.3 + matches * 0.2)  # More matches = higher score

      def _score_follower_range(self, followers: int) -> float:
          """Score based on follower count - sweet spot is 5K-100K."""
          if followers < self.config.target_min_followers:
              return 0.3  # Too small
          elif followers > self.config.target_max_followers:
              return 0.4  # Too big (harder to get noticed)
          elif 5000 <= followers <= 100000:
              return 1.0  # Sweet spot
          else:
              return 0.7  # Good range

      def filter_and_rank(
          self,
          tweets: list[ScrapedTweet]
      ) -> list[tuple[ScrapedTweet, float]]:
          """Filter and rank tweets by score."""
          scored = [(t, self.score(t)) for t in tweets]
          # Filter by threshold
          filtered = [(t, s) for t, s in scored if s >= self.config.score_threshold]
          # Sort by score descending
          return sorted(filtered, key=lambda x: x[1], reverse=True)
  ```

- [ ] **Task 11: Implement ReplyGenerator**
  - File: `src/twitter_bot/reply/generator.py`
  ```python
  REPLY_TYPES = ['expert', 'contrarian', 'question', 'story', 'simplifier']

  REPLY_TYPE_INSTRUCTIONS = {
      'expert': """Add ONE specific insight from your experience that extends their point.
  Pattern: "[Agreement/validation] + [Your specific addition]"
  Must include concrete detail (numbers, specific tech, real example).""",

      'contrarian': """Respectfully push back on ONE aspect while acknowledging the core point.
  Pattern: "[Acknowledge merit] + but [your counterpoint] + [brief why]"
  Not argumentative - thoughtful disagreement that sparks discussion.""",

      'question': """Ask ONE specific question that shows you understood AND thought deeper.
  Pattern: "[Brief context] + [Specific question]?"
  The question should make THEM think, not be easily answered.""",

      'story': """Share a 1-2 sentence personal experience that relates.
  Pattern: "[What happened] + [What you learned]"
  Must be specific (not "I once had this problem too").""",

      'simplifier': """Reframe their point more memorably in fewer words.
  Pattern: "TL;DR: [their point distilled]" or "[Metaphor that captures it]"
  Add a fresh angle they might not have considered.""",
  }

  class ReplyGenerator:
      """Generates viral replies using LLM."""

      def __init__(
          self,
          provider: LLMProvider,
          voice_profile: str,
          state: StateManager
      ):
          self.provider = provider
          self.voice_profile = voice_profile
          self.state = state

      def generate_reply(self, tweet: ScrapedTweet) -> tuple[str, str]:
          """Generate a reply. Returns (reply_text, reply_type)."""
          reply_type = self.state.get_next_reply_type()
          prompt = self._build_prompt(tweet, reply_type)

          result = self.provider.generate(prompt, max_tokens=150)
          reply = self._clean_reply(result.text)

          # Validate length
          if len(reply) > 280:
              reply = reply[:277] + "..."

          return reply, reply_type

      def _build_prompt(self, tweet: ScrapedTweet, reply_type: str) -> str:
          """Build the reply generation prompt."""
          return f"""## CONTEXT
  You are Maxime. 19. Bordeaux. Builder.

  {self.voice_profile}

  You're replying to this tweet:
  ---
  @{tweet.author_handle}:
  "{tweet.content}"
  ---
  Engagement: {tweet.likes} likes, {tweet.retweets} RTs, {tweet.replies} replies

  ## YOUR MISSION
  Write a reply that:
  1. ADDS VALUE - Not "Great take!" but actual insight
  2. STOPS THE SCROLL - First words must hook
  3. SOUNDS LIKE YOU - Builder, direct, no corporate speak
  4. DRIVES ENGAGEMENT - Makes people want to reply to YOU

  ## REPLY TYPE: {reply_type.upper()}

  {REPLY_TYPE_INSTRUCTIONS[reply_type]}

  ## CONSTRAINTS
  - MAX 200 characters (punchy wins)
  - No hashtags ever
  - No links
  - No emojis unless absolutely natural
  - No "I agree" or "This is so true"
  - Sound like a 19-year-old builder, not LinkedIn

  ## BANNED PHRASES
  - "Great post!", "Love this!", "So true!"
  - "Game changer", "Level up", "Unlock"
  - "This is the way", "Couldn't agree more"
  - Starting with "I"
  - Generic praise without substance

  ## YOUR ANGLE
  Connect to YOUR expertise when relevant:
  - AI/ML, LLMs, Claude, GPT
  - Next.js, TypeScript, React, Python
  - Self-Sovereign Identity, DIDs
  - Indie hacking, shipping, building
  - Parkour (discipline, risk, commitment)

  ## OUTPUT
  Reply text only. No quotes. No explanation."""

      def _clean_reply(self, text: str) -> str:
          """Clean up LLM output."""
          text = text.strip()
          # Remove quotes if wrapped
          if text.startswith('"') and text.endswith('"'):
              text = text[1:-1]
          # Remove any "Reply:" prefix
          if text.lower().startswith('reply:'):
              text = text[6:].strip()
          return text
  ```

#### Phase 4: CLI Commands (Tasks 12-14)

- [ ] **Task 12: Add reply-watch command (main daemon)**
  - File: `src/twitter_bot/cli.py`
  ```python
  @app.command(name="reply-watch")
  def reply_watch(
      headless: bool = typer.Option(False, help="Run browser in headless mode"),
      dry_run: bool = typer.Option(False, help="Generate replies but don't post"),
      config_path: Path | None = typer.Option(None, "--config", "-c"),
  ):
      """Watch timeline and reply to high-scoring tweets."""
      settings = get_config(config_path)

      if not settings.reply.enabled:
          console.print("[yellow]Reply bot is disabled in config[/yellow]")
          return

      console.print("[blue]Starting reply watcher...[/blue]")
      console.print(f"  Max replies/day: {settings.reply.max_per_day}")
      console.print(f"  Score threshold: {settings.reply.score_threshold}")
      console.print(f"  Watch interval: {settings.reply.watch_interval_seconds}s")
      console.print("\n[dim]Press Ctrl+C to stop[/dim]\n")

      asyncio.run(_watch_and_reply(settings, headless, dry_run))

  async def _watch_and_reply(settings: Settings, headless: bool, dry_run: bool):
      """Async watch loop."""
      state_manager = StateManager(settings.state_file)
      scorer = TweetScorer(settings.reply, settings.scoring.boost_topics, state_manager)

      provider = get_llm_provider(settings)
      voice_profile = Path(settings.profile.voice_file).expanduser().read_text()
      generator = ReplyGenerator(provider, voice_profile, state_manager)

      cookies_path = Path(settings.reply.cookies_path).expanduser()

      async with StealthBrowser(cookies_path, headless=headless) as browser:
          # Ensure logged in
          if not await browser.ensure_logged_in():
              console.print("[red]Could not log in[/red]")
              return

          console.print("[green]Logged in! Starting watch...[/green]")

          watcher = TimelineWatcher(browser, state_manager)

          async def on_new_tweets(tweets: list[ScrapedTweet]):
              # Check daily limit
              today_count = state_manager.get_replies_today_count(settings.schedule.timezone)
              if today_count >= settings.reply.max_per_day:
                  console.print(f"[yellow]Daily limit reached ({today_count})[/yellow]")
                  return

              # Check delay
              if not state_manager.can_reply_now(settings.reply.min_delay_seconds):
                  return

              # Score and filter
              ranked = scorer.filter_and_rank(tweets)
              if not ranked:
                  return

              # Take best tweet
              best_tweet, score = ranked[0]
              console.print(f"\n[cyan]Found candidate (score: {score:.2f}):[/cyan]")
              console.print(f"  @{best_tweet.author_handle}: {best_tweet.content[:80]}...")

              # Generate reply
              reply, reply_type = generator.generate_reply(best_tweet)
              console.print(f"[green]Generated ({reply_type}):[/green] {reply}")

              if dry_run:
                  console.print("[yellow]DRY RUN - not posting[/yellow]")
                  return

              # Post reply
              try:
                  with TwitterClient(...) as client:
                      result = client.post_reply(reply, best_tweet.tweet_id)
                      console.print(f"[green]Posted![/green] ID: {result.id}")

                      # Record
                      state_manager.record_reply(RepliedTweet(
                          original_tweet_id=best_tweet.tweet_id,
                          original_author=best_tweet.author_handle,
                          original_content=best_tweet.content,
                          reply_tweet_id=result.id,
                          reply_content=reply,
                          reply_type=reply_type,
                          replied_at=datetime.utcnow().isoformat(),
                      ))
              except TwitterAPIError as e:
                  console.print(f"[red]Failed to post:[/red] {e}")

          await watcher.watch(
              interval=settings.reply.watch_interval_seconds,
              on_new_tweets=on_new_tweets
          )
  ```

- [ ] **Task 13: Add reply-once command**
  - File: `src/twitter_bot/cli.py`
  - Action: Single-shot reply (scrape once, reply to best, exit)
  - Useful for testing without running daemon

- [ ] **Task 14: Add reply-status command**
  - File: `src/twitter_bot/cli.py`
  - Action: Show today's replies, stats, config

- [ ] **Task 15: Modify poster bot limits**
  - File: `src/twitter_bot/cli.py`
  - Action: Update `run` command to respect `poster.max_per_day` and `poster.allow_threads`

#### Phase 5: Testing (Tasks 16-18)

- [ ] **Task 16: Add TweetScorer tests**
  - File: `tests/reply/test_scorer.py`
  - Cover: Topic matching, follower scoring, engagement scoring, filtering

- [ ] **Task 17: Add ReplyGenerator tests**
  - File: `tests/reply/test_generator.py`
  - Cover: Prompt building, reply type rotation, output cleaning

- [ ] **Task 18: Add TwitterClient.post_reply tests**
  - File: `tests/twitter/test_client.py`
  - Cover: Success, rate limit, error handling

### Acceptance Criteria

#### Core Functionality

- [ ] **AC1:** Given a running `reply-watch`, when timeline is loaded, then tweets are scraped with content and engagement metrics

- [ ] **AC2:** Given scraped tweets, when scored, then they're ranked by topic relevance + engagement + author size

- [ ] **AC3:** Given a high-scoring tweet, when reply is generated, then it:
  - Is under 280 characters
  - Matches Maxime's voice
  - Uses the correct reply type pattern
  - Adds value (no generic praise)

- [ ] **AC4:** Given a generated reply, when posted via API, then it appears as a reply to the original tweet

- [ ] **AC5:** Given a successful reply, when recorded, then `is_tweet_replied()` returns True

#### Rate Limiting

- [ ] **AC6:** Given daily count >= `max_per_day`, when new tweets arrive, then no reply is posted

- [ ] **AC7:** Given last reply < `min_delay_seconds` ago, when new tweets arrive, then no reply is posted

- [ ] **AC8:** Given a previously replied tweet appears again, then it's excluded from candidates

#### Reply Quality

- [ ] **AC9:** Given 10 consecutive replies, when analyzed, then at least 3 different reply types are used

- [ ] **AC10:** Given a reply generation, when output checked, then it contains no banned phrases

#### Poster Changes

- [ ] **AC11:** Given `poster.allow_threads: false`, when `run` executes, then only single tweets generated

- [ ] **AC12:** Given `poster.max_per_day: 10`, when 10 posts made, then `run --check-schedule` exits

## Additional Context

### Dependencies

```bash
uv add playwright playwright-stealth
playwright install chromium
```

### Running the Bot

```bash
# First run - will prompt for manual login
twitter-bot reply-watch

# With visible browser (recommended for debugging)
twitter-bot reply-watch --no-headless

# Dry run to test without posting
twitter-bot reply-watch --dry-run

# Single shot test
twitter-bot reply-once --dry-run

# Check status
twitter-bot reply-status
```

### Config Example

```yaml
# config.yaml additions

reply:
  enabled: true
  max_per_day: 40
  min_delay_seconds: 120
  max_delay_seconds: 300
  target_min_followers: 1000
  target_max_followers: 500000
  min_engagement_score: 5
  score_threshold: 0.6
  watch_interval_seconds: 45
  cookies_path: "~/.twitter-bot/cookies.json"

poster:
  max_per_day: 10
  allow_threads: false
```

### Testing Strategy

**Unit Tests:**
- TweetScorer scoring logic
- ReplyGenerator prompt building
- Reply type rotation

**Manual Testing:**
1. Run `reply-watch --dry-run` - verify scraping works
2. Check generated replies for quality and voice match
3. Run `reply-once` to test single reply posting
4. Monitor account for any issues

### Notes

**First Run:**
1. Run `reply-watch --no-headless`
2. Browser opens, navigates to Twitter
3. You'll be prompted to log in manually
4. Complete login (including 2FA)
5. Press Enter when done
6. Cookies saved, future runs auto-login

**Keeping It Running:**
- Run in tmux/screen session
- Or use `launchd` for Mac auto-start
- Ctrl+C gracefully saves state

**Prompt Iteration:**
- Monitor reply quality
- Adjust prompt based on results
- Consider A/B testing reply types

**Gradual Rollout:**
- Week 1: `max_per_day: 20`
- Week 2: `max_per_day: 30`
- Week 3+: `max_per_day: 40`

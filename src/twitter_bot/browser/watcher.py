"""Timeline watcher for scraping tweets."""

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from twitter_bot.browser.stealth import StealthBrowser
from twitter_bot.state.manager import StateManager

logger = logging.getLogger(__name__)


@dataclass
class ScrapedTweet:
    """A tweet scraped from the timeline."""

    tweet_id: str
    author_handle: str
    author_name: str
    author_followers: int | None  # May not be available without profile visit
    content: str
    likes: int
    retweets: int
    replies: int
    timestamp: datetime
    is_retweet: bool
    is_quote: bool
    scraped_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class TimelineWatcher:
    """Watches Twitter timeline for new tweets."""

    def __init__(self, browser: StealthBrowser, state: StateManager):
        """Initialize the timeline watcher.

        Args:
            browser: StealthBrowser instance (must be logged in)
            state: StateManager for tracking replied tweets
        """
        self.browser = browser
        self.state = state
        self.seen_tweet_ids: set[str] = set()

    async def scrape_visible_tweets(self) -> list[ScrapedTweet]:
        """Scrape currently visible tweets from the timeline.

        Returns:
            List of ScrapedTweet objects for new (unseen) tweets
        """
        if not self.browser.page:
            return []

        tweets: list[ScrapedTweet] = []

        # Use data-testid attributes (more stable than classes)
        tweet_elements = await self.browser.page.query_selector_all('[data-testid="tweet"]')

        for el in tweet_elements[:30]:  # Limit to 30 per scrape for better candidate pool
            try:
                tweet = await self._parse_tweet_element(el)
                if tweet and tweet.tweet_id not in self.seen_tweet_ids:
                    tweets.append(tweet)
                    self.seen_tweet_ids.add(tweet.tweet_id)
            except Exception as e:
                logger.debug(f"Failed to parse tweet: {e}")
                continue

        if tweets:
            logger.info(f"Scraped {len(tweets)} new tweets")

        return tweets

    async def _parse_tweet_element(self, el) -> ScrapedTweet | None:
        """Parse a tweet element into ScrapedTweet.

        Args:
            el: Playwright ElementHandle for the tweet

        Returns:
            ScrapedTweet or None if parsing fails
        """
        # Extract tweet ID from status link
        link = await el.query_selector('a[href*="/status/"]')
        if not link:
            return None

        href = await link.get_attribute("href")
        if not href or "/status/" not in href:
            return None

        # Extract tweet ID: /username/status/1234567890
        match = re.search(r"/status/(\d+)", href)
        if not match:
            return None
        tweet_id = match.group(1)

        # Extract author info
        author_handle = ""
        author_name = ""
        author_el = await el.query_selector('[data-testid="User-Name"]')
        if author_el:
            # Handle contains @username
            handle_el = await author_el.query_selector('a[href^="/"]')
            if handle_el:
                handle_href = await handle_el.get_attribute("href")
                if handle_href:
                    author_handle = handle_href.strip("/").split("/")[0]

            # Name is usually the first text
            name_spans = await author_el.query_selector_all("span")
            for span in name_spans[:3]:
                text = await span.inner_text()
                if text and not text.startswith("@"):
                    author_name = text.strip()
                    break

        # Extract content
        content = ""
        content_el = await el.query_selector('[data-testid="tweetText"]')
        if content_el:
            content = await content_el.inner_text()
            content = content.strip()

        # Extract metrics (likes, RTs, replies)
        metrics = await self._extract_metrics(el)

        # Check if retweet or quote
        is_retweet = await el.query_selector('[data-testid="socialContext"]') is not None
        is_quote = await el.query_selector('[data-testid="quoteTweet"]') is not None

        return ScrapedTweet(
            tweet_id=tweet_id,
            author_handle=author_handle,
            author_name=author_name,
            author_followers=None,  # Would need profile visit to get this
            content=content,
            likes=metrics.get("likes", 0),
            retweets=metrics.get("retweets", 0),
            replies=metrics.get("replies", 0),
            timestamp=datetime.now(UTC),  # Approximate - actual time would need parsing
            is_retweet=is_retweet,
            is_quote=is_quote,
        )

    async def _extract_metrics(self, el) -> dict[str, int]:
        """Extract engagement metrics from a tweet element.

        Args:
            el: Playwright ElementHandle for the tweet

        Returns:
            Dict with likes, retweets, replies counts
        """
        metrics = {"likes": 0, "retweets": 0, "replies": 0}

        # Metrics are in aria-label attributes
        # Reply button: "X Replies"
        # Retweet button: "X Reposts" or "X Retweets"
        # Like button: "X Likes"

        try:
            # Reply count
            reply_btn = await el.query_selector('[data-testid="reply"]')
            if reply_btn:
                aria = await reply_btn.get_attribute("aria-label")
                if aria:
                    count = self._parse_count(aria)
                    metrics["replies"] = count

            # Retweet count
            retweet_btn = await el.query_selector('[data-testid="retweet"]')
            if retweet_btn:
                aria = await retweet_btn.get_attribute("aria-label")
                if aria:
                    count = self._parse_count(aria)
                    metrics["retweets"] = count

            # Like count
            like_btn = await el.query_selector('[data-testid="like"]')
            if like_btn:
                aria = await like_btn.get_attribute("aria-label")
                if aria:
                    count = self._parse_count(aria)
                    metrics["likes"] = count
        except Exception as e:
            logger.debug(f"Error extracting metrics: {e}")

        return metrics

    def _parse_count(self, aria_label: str) -> int:
        """Parse count from aria-label like '5 Replies' or '1.2K Likes'.

        Args:
            aria_label: The aria-label string

        Returns:
            Integer count
        """
        if not aria_label:
            return 0

        # Extract number part
        match = re.search(r"([\d,.]+)\s*([KMB])?", aria_label, re.IGNORECASE)
        if not match:
            return 0

        num_str = match.group(1).replace(",", "")
        try:
            num = float(num_str)
        except ValueError:
            return 0

        # Handle suffixes
        suffix = match.group(2)
        if suffix:
            suffix = suffix.upper()
            if suffix == "K":
                num *= 1000
            elif suffix == "M":
                num *= 1_000_000
            elif suffix == "B":
                num *= 1_000_000_000

        return int(num)

    async def watch(
        self,
        interval: int = 45,
        on_new_tweets: Callable[[list[ScrapedTweet]], Awaitable[None]] | None = None,
    ) -> None:
        """Watch timeline continuously, calling callback on new tweets.

        Args:
            interval: Base interval between checks in seconds
            on_new_tweets: Async callback when new tweets are found

        Note:
            This runs indefinitely. Use Ctrl+C to stop.
        """
        if not self.browser.page:
            logger.error("Browser page not available")
            return

        # Navigate to home timeline
        await self.browser.page.goto("https://x.com/home", wait_until="domcontentloaded")
        await self.browser.random_delay(2, 4)

        logger.info(f"Starting timeline watch (interval: {interval}s)")

        while True:
            try:
                # Scroll down slightly to trigger loading
                await self.browser.scroll_down(300)
                await self.browser.random_delay(1, 2)

                # Scrape visible tweets
                new_tweets = await self.scrape_visible_tweets()

                if new_tweets and on_new_tweets:
                    await on_new_tweets(new_tweets)

                # Scroll back to top
                await self.browser.scroll_to_top()
                await self.browser.random_delay(1, 2)

                # Refresh to get latest
                await self.browser.refresh()

                # Wait with some randomness (0.8x to 1.2x interval)
                wait_time = interval * (0.8 + 0.4 * (hash(str(datetime.now(UTC))) % 100) / 100)
                logger.debug(f"Waiting {wait_time:.1f}s before next check")
                await asyncio.sleep(wait_time)

            except asyncio.CancelledError:
                logger.info("Watch loop cancelled")
                break
            except Exception as e:
                logger.error(f"Watch loop error: {e}")
                # Back off on error
                await asyncio.sleep(30)

    async def scrape_once(self) -> list[ScrapedTweet]:
        """Scrape timeline once and return tweets.

        Returns:
            List of ScrapedTweet objects
        """
        if not self.browser.page:
            return []

        # Navigate to home timeline
        await self.browser.page.goto("https://x.com/home", wait_until="domcontentloaded")
        await self.browser.random_delay(2, 4)

        # Scroll down a few times to load more tweets
        all_tweets: list[ScrapedTweet] = []

        for _ in range(3):
            tweets = await self.scrape_visible_tweets()
            all_tweets.extend(tweets)
            await self.browser.scroll_down(500)
            await self.browser.random_delay(1, 2)

        logger.info(f"Scraped {len(all_tweets)} total tweets")
        return all_tweets

    async def like_tweet(self, tweet: ScrapedTweet) -> bool:
        """Like a tweet by clicking its like button.

        Args:
            tweet: The tweet to like

        Returns:
            True if like succeeded, False otherwise
        """
        if not self.browser.page:
            return False

        try:
            # Find the tweet element by looking for the status link
            tweet_selector = f'a[href*="/status/{tweet.tweet_id}"]'
            tweet_link = await self.browser.page.query_selector(tweet_selector)

            if not tweet_link:
                logger.debug(f"Could not find tweet {tweet.tweet_id} on page")
                return False

            # Find the parent tweet container
            tweet_el = await tweet_link.evaluate_handle(
                """el => {
                    let parent = el;
                    while (parent && !parent.getAttribute('data-testid')?.includes('tweet')) {
                        parent = parent.parentElement;
                    }
                    return parent;
                }"""
            )

            if not tweet_el:
                return False

            # Find and click the like button within this tweet
            like_btn = await tweet_el.as_element().query_selector('[data-testid="like"]')
            if not like_btn:
                # Maybe already liked - check for unlike button
                unlike_btn = await tweet_el.as_element().query_selector('[data-testid="unlike"]')
                if unlike_btn:
                    logger.debug(f"Tweet {tweet.tweet_id} already liked")
                    return True
                return False

            # Human-like delay before clicking
            await self.browser.random_delay(0.3, 0.8)
            await like_btn.click()
            await self.browser.random_delay(0.5, 1.0)

            logger.info(f"Liked tweet {tweet.tweet_id} by @{tweet.author_handle}")
            return True

        except Exception as e:
            logger.debug(f"Failed to like tweet {tweet.tweet_id}: {e}")
            return False

    async def like_tweet_on_page(self, tweet_id: str) -> bool:
        """Like a tweet that's currently visible on the page.

        Args:
            tweet_id: The tweet ID to like

        Returns:
            True if like succeeded
        """
        if not self.browser.page:
            return False

        try:
            # Find all tweets and look for the one with this ID
            tweet_elements = await self.browser.page.query_selector_all('[data-testid="tweet"]')

            for el in tweet_elements:
                link = await el.query_selector(f'a[href*="/status/{tweet_id}"]')
                if link:
                    # Found the tweet, now click like
                    like_btn = await el.query_selector('[data-testid="like"]')
                    if like_btn:
                        await self.browser.random_delay(0.2, 0.5)
                        await like_btn.click()
                        await self.browser.random_delay(0.3, 0.7)
                        logger.info(f"Liked tweet {tweet_id}")
                        return True
                    else:
                        # Check if already liked
                        unlike_btn = await el.query_selector('[data-testid="unlike"]')
                        if unlike_btn:
                            logger.debug(f"Tweet {tweet_id} already liked")
                            return True
                    break

            return False
        except Exception as e:
            logger.debug(f"Failed to like tweet {tweet_id}: {e}")
            return False

    async def quote_tweet_on_page(self, tweet_id: str, quote_text: str) -> bool:
        """Quote tweet a post that's currently visible on the page.

        Args:
            tweet_id: The tweet ID to quote
            quote_text: The text to add as a quote comment

        Returns:
            True if quote succeeded
        """
        if not self.browser.page:
            return False

        try:
            # Find all tweets and look for the one with this ID
            tweet_elements = await self.browser.page.query_selector_all('[data-testid="tweet"]')

            for el in tweet_elements:
                link = await el.query_selector(f'a[href*="/status/{tweet_id}"]')
                if link:
                    # Found the tweet, now click the retweet button to open menu
                    retweet_btn = await el.query_selector('[data-testid="retweet"]')
                    if not retweet_btn:
                        logger.debug(f"No retweet button found for tweet {tweet_id}")
                        return False

                    await self.browser.random_delay(0.3, 0.6)
                    await retweet_btn.click()
                    await self.browser.random_delay(0.5, 1.0)

                    # Click "Quote" option from the dropdown menu
                    # The dropdown has data-testid="Dropdown" and Quote option is the second item
                    quote_option = await self.browser.page.query_selector(
                        '[data-testid="Dropdown"] [role="menuitem"]:nth-child(2)'
                    )
                    if not quote_option:
                        # Try alternative selector for quote button
                        quote_option = await self.browser.page.query_selector(
                            'div[role="menuitem"] span:text-is("Quote")'
                        )
                    if not quote_option:
                        # Fallback: look for any menuitem containing "Quote"
                        menu_items = await self.browser.page.query_selector_all('[role="menuitem"]')
                        for item in menu_items:
                            text = await item.inner_text()
                            if "quote" in text.lower():
                                quote_option = item
                                break

                    if not quote_option:
                        logger.debug(f"Could not find Quote option in dropdown for tweet {tweet_id}")
                        # Close the dropdown by pressing Escape
                        await self.browser.page.keyboard.press("Escape")
                        return False

                    await self.browser.random_delay(0.2, 0.5)
                    await quote_option.click()
                    await self.browser.random_delay(1.0, 2.0)

                    # Now we should be in the quote tweet modal
                    # Find the text input area
                    text_input = await self.browser.page.query_selector(
                        '[data-testid="tweetTextarea_0"]'
                    )
                    if not text_input:
                        # Alternative selector
                        text_input = await self.browser.page.query_selector(
                            'div[role="textbox"][contenteditable="true"]'
                        )

                    if not text_input:
                        logger.debug("Could not find text input for quote tweet")
                        await self.browser.page.keyboard.press("Escape")
                        return False

                    # Type the quote text naturally
                    await text_input.click()
                    await self.browser.random_delay(0.3, 0.6)

                    # Type character by character with small delays for human-like behavior
                    for char in quote_text:
                        await self.browser.page.keyboard.type(char, delay=30 + int(50 * (hash(char) % 100) / 100))

                    await self.browser.random_delay(0.5, 1.0)

                    # Click the post button
                    post_btn = await self.browser.page.query_selector('[data-testid="tweetButton"]')
                    if not post_btn:
                        post_btn = await self.browser.page.query_selector(
                            'button[data-testid="tweetButtonInline"]'
                        )

                    if not post_btn:
                        logger.debug("Could not find post button for quote tweet")
                        await self.browser.page.keyboard.press("Escape")
                        return False

                    await self.browser.random_delay(0.3, 0.7)
                    await post_btn.click()
                    await self.browser.random_delay(1.5, 2.5)

                    logger.info(f"Quote tweeted {tweet_id}: {quote_text[:50]}...")
                    return True

            logger.debug(f"Could not find tweet {tweet_id} on page")
            return False

        except Exception as e:
            logger.debug(f"Failed to quote tweet {tweet_id}: {e}")
            # Try to close any open modals
            try:
                await self.browser.page.keyboard.press("Escape")
            except Exception:
                pass
            return False

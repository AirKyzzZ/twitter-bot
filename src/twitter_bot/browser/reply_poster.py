"""Browser-based reply posting with human-like behavior."""

import logging

from twitter_bot.browser.stealth import StealthBrowser
from twitter_bot.browser.watcher import ScrapedTweet

logger = logging.getLogger(__name__)


class BrowserReplyPoster:
    """Posts replies using browser automation instead of API."""

    # Twitter selectors (data-testid attributes)
    REPLY_TEXTAREA = '[data-testid="tweetTextarea_0"]'
    SUBMIT_BUTTON = '[data-testid="tweetButton"]'
    SUBMIT_BUTTON_ALT = '[data-testid="tweetButtonInline"]'
    REPLY_SUCCESS_INDICATOR = '[data-testid="toast"]'

    def __init__(self, browser: StealthBrowser):
        """Initialize the reply poster.

        Args:
            browser: An active StealthBrowser instance
        """
        self.browser = browser

    async def post_reply(
        self, tweet: ScrapedTweet, reply_text: str
    ) -> tuple[bool, str | None]:
        """Post a reply to a tweet using browser automation.

        Args:
            tweet: The tweet to reply to
            reply_text: The reply content

        Returns:
            Tuple of (success, error_message)
        """
        if not self.browser.page:
            return False, "Browser page not available"

        tweet_url = f"https://x.com/{tweet.author_handle}/status/{tweet.tweet_id}"
        logger.info(f"Navigating to tweet: {tweet_url}")

        try:
            # Navigate to the tweet page
            await self.browser.page.goto(tweet_url, wait_until="domcontentloaded")
            await self.browser.random_delay(2, 4)

            # Wait for reply textarea to be available
            if not await self.browser.wait_for_selector(self.REPLY_TEXTAREA, timeout=10000):
                return False, "Reply textarea not found"

            # Click on the reply textarea to focus it
            if not await self.browser.click(self.REPLY_TEXTAREA):
                return False, "Failed to click reply textarea"

            await self.browser.random_delay(0.5, 1.0)

            # Type the reply with human-like delays
            if not await self.browser.type_like_human(self.REPLY_TEXTAREA, reply_text):
                return False, "Failed to type reply"

            await self.browser.random_delay(0.5, 1.5)

            # Click the submit button
            submitted = await self.browser.click(self.SUBMIT_BUTTON)
            if not submitted:
                # Try alternative submit button
                submitted = await self.browser.click(self.SUBMIT_BUTTON_ALT)

            if not submitted:
                return False, "Failed to click submit button"

            # Wait for success indication (toast notification or URL change)
            await self.browser.random_delay(2, 4)

            # Verify success by checking if we can see the reply or a success toast
            success = await self._verify_post_success()

            if success:
                logger.info("Reply posted successfully via browser")
                return True, None
            else:
                return False, "Could not verify reply was posted"

        except Exception as e:
            logger.error(f"Browser reply failed: {e}")
            return False, str(e)

    async def _verify_post_success(self) -> bool:
        """Verify that the reply was posted successfully.

        Returns:
            True if reply appears to have been posted
        """
        if not self.browser.page:
            return False

        # Check for success indicators:
        # 1. Toast notification
        # 2. Reply textarea is now empty
        # 3. New tweet appears in the thread

        try:
            # Check if textarea is empty (success indicator)
            textarea = await self.browser.page.query_selector(self.REPLY_TEXTAREA)
            if textarea:
                text_content = await textarea.text_content()
                if not text_content or text_content.strip() == "":
                    return True

            # Check for toast notification
            toast = await self.browser.page.query_selector(self.REPLY_SUCCESS_INDICATOR)
            if toast:
                return True

            # Fallback: assume success if no error visible
            error_indicators = [
                '[data-testid="error"]',
                '[role="alert"]',
            ]
            for selector in error_indicators:
                error = await self.browser.page.query_selector(selector)
                if error:
                    error_text = await error.text_content()
                    logger.warning(f"Error indicator found: {error_text}")
                    return False

            # No error found - assume success
            return True

        except Exception as e:
            logger.warning(f"Error verifying post success: {e}")
            return False  # Conservative: assume failure if verification fails

    async def return_to_timeline(self) -> bool:
        """Navigate back to the home timeline.

        Returns:
            True if navigation successful
        """
        if not self.browser.page:
            return False

        try:
            await self.browser.page.goto(
                "https://x.com/home", wait_until="domcontentloaded"
            )
            await self.browser.random_delay(2, 3)
            return True
        except Exception as e:
            logger.warning(f"Failed to return to timeline: {e}")
            return False

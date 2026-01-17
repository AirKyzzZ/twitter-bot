"""Stealth browser management with Playwright."""

import asyncio
import json
import logging
import random
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

# Create stealth instance for applying anti-detection patches
_stealth = Stealth(
    navigator_platform_override="MacIntel",
    navigator_vendor_override="Google Inc.",
)


class StealthBrowser:
    """Manages Playwright browser with stealth patches for Twitter."""

    def __init__(self, cookies_path: Path, headless: bool = False):
        """Initialize the stealth browser.

        Args:
            cookies_path: Path to store/load session cookies
            headless: Whether to run in headless mode (visible browser recommended)
        """
        self.cookies_path = Path(cookies_path).expanduser()
        self.headless = headless
        self._playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def __aenter__(self) -> "StealthBrowser":
        """Launch browser and restore session."""
        self._playwright = await async_playwright().start()

        # Launch Chromium with stealth args
        self.browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        # Create context with realistic settings
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="Europe/Paris",
        )

        # Load cookies if they exist
        if self.cookies_path.exists():
            try:
                cookies = json.loads(self.cookies_path.read_text())
                await self.context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies from {self.cookies_path}")
            except Exception as e:
                logger.warning(f"Failed to load cookies: {e}")

        # Create page and apply stealth
        self.page = await self.context.new_page()
        await _stealth.apply_stealth_async(self.page)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Save cookies and close browser."""
        if self.context:
            try:
                cookies = await self.context.cookies()
                self.cookies_path.parent.mkdir(parents=True, exist_ok=True)
                self.cookies_path.write_text(json.dumps(cookies, indent=2))
                logger.info(f"Saved {len(cookies)} cookies to {self.cookies_path}")
            except Exception as e:
                logger.warning(f"Failed to save cookies: {e}")

        if self.browser:
            await self.browser.close()

        if self._playwright:
            await self._playwright.stop()

    async def random_delay(self, min_s: float = 1.0, max_s: float = 3.0) -> None:
        """Human-like random delay.

        Args:
            min_s: Minimum delay in seconds
            max_s: Maximum delay in seconds
        """
        delay = random.uniform(min_s, max_s)
        await asyncio.sleep(delay)

    async def ensure_logged_in(self) -> bool:
        """Check if logged in, prompt for manual login if not.

        Returns:
            True if successfully logged in
        """
        if not self.page:
            return False

        # Use x.com (where cookies are) and don't wait for networkidle (Twitter never stops)
        await self.page.goto("https://x.com/home", wait_until="domcontentloaded")
        await self.random_delay(3, 5)

        # Check for login indicators - the compose tweet button or primary column
        logged_in_selectors = [
            '[data-testid="SideNav_NewTweet_Button"]',
            '[data-testid="primaryColumn"]',
            '[aria-label="Home timeline"]',
        ]

        for selector in logged_in_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=5000)
                if element:
                    logger.info("Already logged in to Twitter")
                    return True
            except Exception:
                continue

        # Not logged in - prompt for manual login
        print("\n" + "=" * 60)
        print("NOT LOGGED IN TO TWITTER")
        print("=" * 60)
        print("\nPlease log in manually in the browser window.")
        print("Complete any 2FA if required.")
        print("\nPress Enter when you're done logging in...")
        print("=" * 60 + "\n")

        # Wait for user input (blocking)
        await asyncio.get_running_loop().run_in_executor(None, input)

        # Check again
        await self.page.goto("https://x.com/home", wait_until="domcontentloaded")
        await self.random_delay(3, 5)

        for selector in logged_in_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=10000)
                if element:
                    logger.info("Successfully logged in to Twitter")
                    return True
            except Exception:
                continue

        logger.error("Failed to verify login")
        return False

    async def scroll_down(self, pixels: int = 300) -> None:
        """Scroll down the page.

        Args:
            pixels: Number of pixels to scroll
        """
        if self.page:
            await self.page.evaluate(f"window.scrollBy(0, {pixels})")
            await self.random_delay(0.5, 1.0)

    async def scroll_to_top(self) -> None:
        """Scroll to the top of the page."""
        if self.page:
            await self.page.evaluate("window.scrollTo(0, 0)")
            await self.random_delay(0.5, 1.0)

    async def refresh(self) -> None:
        """Refresh the current page."""
        if self.page:
            await self.page.reload(wait_until="domcontentloaded")
            await self.random_delay(2, 4)

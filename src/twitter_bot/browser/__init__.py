"""Browser automation module for Twitter timeline scraping."""

from twitter_bot.browser.stealth import StealthBrowser
from twitter_bot.browser.watcher import ScrapedTweet, TimelineWatcher

__all__ = ["StealthBrowser", "TimelineWatcher", "ScrapedTweet"]

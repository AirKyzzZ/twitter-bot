"""APScheduler-based daemon for autonomous operation."""

import logging
import random
import signal
import sys
import time
from collections.abc import Callable
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class DaemonScheduler:
    """Manages the autonomous posting schedule."""

    def __init__(
        self,
        run_cycle: Callable[[], None],
        tweets_per_day: int = 30,
        active_hours: str = "08:00-22:00",
        timezone: str = "UTC",
    ):
        """Initialize the daemon scheduler.

        Args:
            run_cycle: Function to call for each posting cycle
            tweets_per_day: Target number of tweets per day
            active_hours: Active posting hours (e.g., "08:00-22:00")
            timezone: Timezone for scheduling
        """
        self.run_cycle = run_cycle
        self.tweets_per_day = tweets_per_day
        self.active_hours = active_hours
        self.timezone = timezone
        self._scheduler: BackgroundScheduler | None = None
        self._running = False

    def _parse_active_hours(self) -> tuple[int, int]:
        """Parse active hours string into start and end hours."""
        try:
            start, end = self.active_hours.split("-")
            start_hour = int(start.split(":")[0])
            end_hour = int(end.split(":")[0])
            return start_hour, end_hour
        except Exception:
            return 8, 22  # Default fallback

    def _calculate_interval_minutes(self) -> int:
        """Calculate interval between posts in minutes."""
        start_hour, end_hour = self._parse_active_hours()
        active_hours = end_hour - start_hour
        if active_hours <= 0:
            active_hours = 14  # Default to 14 hours

        # Minutes per day during active hours
        active_minutes = active_hours * 60

        # Interval between tweets
        interval = active_minutes // self.tweets_per_day

        # Minimum 2 minutes between tweets
        return max(2, interval)

    def _is_within_active_hours(self) -> bool:
        """Check if current time is within active hours."""
        from zoneinfo import ZoneInfo

        start_hour, end_hour = self._parse_active_hours()
        tz = ZoneInfo(self.timezone)
        current_hour = datetime.now(tz).hour
        return start_hour <= current_hour < end_hour

    def _wrapped_run_cycle(self, skip_jitter: bool = False) -> None:
        """Wrapper that checks active hours and adds jitter before running."""
        if not self._is_within_active_hours():
            logger.debug("Outside active hours, skipping cycle")
            return

        # Add random jitter (0-5 minutes) to avoid predictable posting patterns
        if not skip_jitter:
            jitter_seconds = random.randint(0, 300)  # 0-5 minutes
            logger.debug(f"Adding {jitter_seconds}s jitter before posting")
            time.sleep(jitter_seconds)

        try:
            logger.info("Starting posting cycle")
            self.run_cycle()
            logger.info("Posting cycle completed")
        except Exception as e:
            logger.error(f"Posting cycle failed: {e}")

    def _handle_shutdown(self, signum, frame) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def start(self) -> None:
        """Start the daemon scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        interval_minutes = self._calculate_interval_minutes()
        logger.info(
            f"Starting daemon: {self.tweets_per_day} tweets/day, "
            f"interval={interval_minutes}min, active={self.active_hours}"
        )

        self._scheduler = BackgroundScheduler(timezone=self.timezone)
        self._scheduler.add_job(
            self._wrapped_run_cycle,
            IntervalTrigger(minutes=interval_minutes),
            id="posting_cycle",
            name="Autonomous posting cycle",
            replace_existing=True,
        )

        self._scheduler.start()
        self._running = True

        # Run first cycle immediately (no jitter for first run)
        self._wrapped_run_cycle(skip_jitter=True)

    def stop(self) -> None:
        """Stop the daemon scheduler."""
        if self._scheduler and self._running:
            logger.info("Stopping scheduler...")
            self._scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Scheduler stopped")

    def run_forever(self) -> None:
        """Start scheduler and block until shutdown."""
        self.start()

        try:
            # Keep the main thread alive
            while self._running:
                signal.pause()
        except (KeyboardInterrupt, SystemExit):
            self.stop()

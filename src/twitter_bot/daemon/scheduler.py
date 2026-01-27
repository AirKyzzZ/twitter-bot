"""APScheduler-based daemon for autonomous operation with smart timing."""

import logging
import random
import signal
import sys
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


# Peak hours for Twitter engagement (Paris time)
# DATA-DRIVEN: 9h, 12h, 13h are the best times
PEAK_HOURS = [9, 12, 13]
GOOD_HOURS = [10, 11, 14]  # Secondary peak


class SmartScheduler:
    """Smart scheduler that concentrates posts during peak engagement hours.
    
    Twitter Algorithm 2026 insights:
    - Tweet loses 50% boost every 6h - first hour is critical
    - Peak times: 9h-14h (9h, 12h, 13h especially)
    - Media (image/video): 2x boost vs text-only
    """

    def __init__(
        self,
        run_cycle: Callable[[], None],
        tweets_per_day: int = 15,
        active_hours: str = "09:00-14:00",
        timezone: str = "Europe/Paris",
    ):
        self.run_cycle = run_cycle
        self.tweets_per_day = min(tweets_per_day, 16)  # API limit safety
        self.active_hours = active_hours
        self.timezone = timezone
        self._scheduler: BackgroundScheduler | None = None
        self._running = False
        self._posted_today = 0
        self._last_reset_date: str | None = None

    def _parse_active_hours(self) -> tuple[int, int]:
        """Parse active hours string into start and end hours."""
        try:
            start, end = self.active_hours.split("-")
            start_hour = int(start.split(":")[0])
            end_hour = int(end.split(":")[0])
            return start_hour, end_hour
        except Exception:
            return 9, 14  # Default to peak hours

    def _get_smart_schedule(self) -> list[tuple[int, int]]:
        """Generate smart posting times concentrated around peak hours.
        
        Returns list of (hour, minute) tuples for today's posts.
        Strategy:
        - 40% of posts at peak hours (9, 12, 13)
        - 40% at good hours (10, 11, 14)
        - 20% randomly distributed
        - Add jitter to minutes (0-55) to avoid predictability
        """
        start_hour, end_hour = self._parse_active_hours()
        schedule = []
        
        # Calculate distribution
        peak_count = int(self.tweets_per_day * 0.4)  # 40% at peak
        good_count = int(self.tweets_per_day * 0.4)  # 40% at good hours
        random_count = self.tweets_per_day - peak_count - good_count  # Rest random
        
        # Add peak hour slots
        for _ in range(peak_count):
            hour = random.choice(PEAK_HOURS)
            if start_hour <= hour <= end_hour:
                minute = random.randint(0, 55)
                schedule.append((hour, minute))
        
        # Add good hour slots
        for _ in range(good_count):
            hour = random.choice(GOOD_HOURS)
            if start_hour <= hour <= end_hour:
                minute = random.randint(0, 55)
                schedule.append((hour, minute))
        
        # Add random slots within active hours
        for _ in range(random_count):
            hour = random.randint(start_hour, end_hour)
            minute = random.randint(0, 55)
            schedule.append((hour, minute))
        
        # Sort by time and ensure minimum spacing (15 minutes)
        schedule.sort()
        spaced_schedule = []
        last_time = None
        
        for hour, minute in schedule:
            current = hour * 60 + minute
            if last_time is None or current - last_time >= 15:
                spaced_schedule.append((hour, minute))
                last_time = current
        
        return spaced_schedule[:self.tweets_per_day]

    def _get_next_slot(self) -> tuple[int, int] | None:
        """Get the next posting slot for today."""
        tz = ZoneInfo(self.timezone)
        now = datetime.now(tz)
        current_minutes = now.hour * 60 + now.minute
        
        schedule = self._get_smart_schedule()
        
        for hour, minute in schedule:
            slot_minutes = hour * 60 + minute
            if slot_minutes > current_minutes:
                return (hour, minute)
        
        return None  # No more slots today

    def _is_within_active_hours(self) -> bool:
        """Check if current time is within active hours."""
        start_hour, end_hour = self._parse_active_hours()
        tz = ZoneInfo(self.timezone)
        current_hour = datetime.now(tz).hour
        return start_hour <= current_hour < end_hour

    def _reset_daily_counter(self) -> None:
        """Reset daily counter if it's a new day."""
        tz = ZoneInfo(self.timezone)
        today = datetime.now(tz).strftime("%Y-%m-%d")
        
        if self._last_reset_date != today:
            self._posted_today = 0
            self._last_reset_date = today
            logger.info(f"New day {today}, reset counter")

    def _wrapped_run_cycle(self, skip_jitter: bool = False) -> None:
        """Wrapper that checks limits and adds jitter before running."""
        self._reset_daily_counter()
        
        if not self._is_within_active_hours():
            logger.debug("Outside active hours, skipping cycle")
            return
        
        if self._posted_today >= self.tweets_per_day:
            logger.info(f"Daily limit reached ({self._posted_today}/{self.tweets_per_day})")
            return

        # Add random jitter (0-3 minutes) to avoid predictable posting patterns
        if not skip_jitter:
            jitter_seconds = random.randint(0, 180)  # 0-3 minutes
            logger.debug(f"Adding {jitter_seconds}s jitter before posting")
            time.sleep(jitter_seconds)

        try:
            logger.info(f"Starting posting cycle ({self._posted_today + 1}/{self.tweets_per_day})")
            self.run_cycle()
            self._posted_today += 1
            logger.info(f"Posting cycle completed ({self._posted_today}/{self.tweets_per_day})")
        except Exception as e:
            logger.error(f"Posting cycle failed: {e}")

    def _handle_shutdown(self, signum, frame) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def start(self) -> None:
        """Start the daemon scheduler with smart timing."""
        if self._running:
            logger.warning("Scheduler is already running")
            return

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        start_hour, end_hour = self._parse_active_hours()
        logger.info(
            f"Starting smart scheduler: {self.tweets_per_day} tweets/day, "
            f"peak hours={start_hour}:00-{end_hour}:00 {self.timezone}"
        )

        self._scheduler = BackgroundScheduler(timezone=self.timezone)
        
        # Schedule jobs for each hour in the active window
        for hour in range(start_hour, end_hour + 1):
            # Multiple jobs per hour for flexibility
            for minute in [0, 15, 30, 45]:
                self._scheduler.add_job(
                    self._wrapped_run_cycle,
                    CronTrigger(hour=hour, minute=minute),
                    id=f"posting_cycle_{hour}_{minute}",
                    name=f"Posting at {hour}:{minute:02d}",
                    replace_existing=True,
                )

        self._scheduler.start()
        self._running = True

        # Run first cycle immediately if within active hours (no jitter for first run)
        if self._is_within_active_hours():
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


# Backward compatibility alias
DaemonScheduler = SmartScheduler

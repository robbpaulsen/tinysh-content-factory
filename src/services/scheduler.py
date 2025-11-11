"""YouTube video scheduling service."""

import logging
from datetime import datetime, timedelta
from typing import List

import pytz

from src.config import settings

logger = logging.getLogger(__name__)


class VideoScheduler:
    """Service for calculating YouTube video publish schedules."""

    def __init__(
        self,
        timezone: str | None = None,
        start_hour: int | None = None,
        end_hour: int | None = None,
        interval_hours: int | None = None,
    ):
        """
        Initialize scheduler with configuration.

        Args:
            timezone: Timezone for scheduling (default: from settings)
            start_hour: First video hour (0-23, default: from settings)
            end_hour: Last video hour (0-23, default: from settings)
            interval_hours: Hours between videos (default: from settings)
        """
        self.timezone = pytz.timezone(timezone or settings.youtube_timezone)
        self.start_hour = start_hour if start_hour is not None else settings.youtube_schedule_start_hour
        self.end_hour = end_hour if end_hour is not None else settings.youtube_schedule_end_hour
        self.interval_hours = interval_hours if interval_hours is not None else settings.youtube_schedule_interval_hours

        # Validate configuration
        if self.start_hour >= self.end_hour:
            raise ValueError(f"start_hour ({self.start_hour}) must be less than end_hour ({self.end_hour})")

        # Calculate slots per day
        self.slots_per_day = self._calculate_slots_per_day()

        logger.info(f"Scheduler initialized: {self.slots_per_day} videos/day")
        logger.info(f"Schedule: {self.start_hour}:00 to {self.end_hour}:00 every {self.interval_hours}h ({self.timezone})")

    def _calculate_slots_per_day(self) -> int:
        """Calculate how many video slots fit in one day."""
        available_hours = self.end_hour - self.start_hour
        slots = (available_hours // self.interval_hours) + 1
        return slots

    def calculate_schedule(
        self,
        video_count: int,
        start_date: datetime | None = None,
    ) -> List[datetime]:
        """
        Calculate publish schedule for multiple videos.

        Args:
            video_count: Number of videos to schedule
            start_date: Start date (default: tomorrow at start_hour in configured timezone)

        Returns:
            List of datetime objects in UTC for each video publish time

        Example:
            With defaults (6 AM, 4 PM, 2h interval):
            - Day 1: 6 AM, 8 AM, 10 AM, 12 PM, 2 PM, 4 PM (6 videos)
            - Day 2: 6 AM, 8 AM, 10 AM, 12 PM, 2 PM, 4 PM (6 videos)
            - And so on...
        """
        if video_count <= 0:
            return []

        # Default start: tomorrow at start_hour in configured timezone
        if start_date is None:
            now_local = datetime.now(self.timezone)
            tomorrow = now_local + timedelta(days=1)
            start_date = tomorrow.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
        elif start_date.tzinfo is None:
            # If naive datetime, localize to configured timezone
            start_date = self.timezone.localize(start_date)
        else:
            # If aware datetime, convert to configured timezone
            start_date = start_date.astimezone(self.timezone)

        # Ensure start time is at start_hour
        if start_date.hour < self.start_hour:
            start_date = start_date.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
        elif start_date.hour > self.end_hour:
            # If after end hour, move to next day
            start_date = start_date + timedelta(days=1)
            start_date = start_date.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)

        schedule = []
        current_date = start_date

        for i in range(video_count):
            # Calculate slot within the day (0 to slots_per_day-1)
            slot_in_day = i % self.slots_per_day

            if i > 0 and slot_in_day == 0:
                # Move to next day, reset to start_hour
                current_date = current_date + timedelta(days=1)
                current_date = current_date.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)

            # Calculate hour for this slot
            publish_hour = self.start_hour + (slot_in_day * self.interval_hours)
            publish_time = current_date.replace(hour=publish_hour, minute=0, second=0, microsecond=0)

            # Convert to UTC for YouTube API
            publish_time_utc = publish_time.astimezone(pytz.UTC)
            schedule.append(publish_time_utc)

        logger.info(f"Generated schedule for {video_count} videos over {(video_count // self.slots_per_day) + 1} days")
        logger.debug(f"First publish: {schedule[0].strftime('%Y-%m-%d %H:%M %Z')}")
        logger.debug(f"Last publish: {schedule[-1].strftime('%Y-%m-%d %H:%M %Z')}")

        return schedule

    def get_schedule_summary(self, schedule: List[datetime]) -> str:
        """
        Get human-readable summary of schedule.

        Args:
            schedule: List of publish times (UTC)

        Returns:
            Multi-line summary string
        """
        if not schedule:
            return "No videos scheduled"

        # Convert to local timezone for display
        schedule_local = [dt.astimezone(self.timezone) for dt in schedule]

        summary_lines = [
            f"Schedule Summary ({self.timezone}):",
            f"Total videos: {len(schedule)}",
            f"First publish: {schedule_local[0].strftime('%Y-%m-%d %H:%M')}",
            f"Last publish: {schedule_local[-1].strftime('%Y-%m-%d %H:%M')}",
            f"",
            "Daily breakdown:",
        ]

        # Group by date
        by_date = {}
        for dt in schedule_local:
            date_key = dt.date()
            if date_key not in by_date:
                by_date[date_key] = []
            by_date[date_key].append(dt)

        for date, times in sorted(by_date.items()):
            time_str = ", ".join([t.strftime("%H:%M") for t in times])
            summary_lines.append(f"  {date}: {len(times)} videos at {time_str}")

        return "\n".join(summary_lines)

    def validate_schedule(self, schedule: List[datetime]) -> bool:
        """
        Validate that schedule follows the rules.

        Args:
            schedule: List of publish times (UTC)

        Returns:
            True if valid, raises ValueError if invalid
        """
        if not schedule:
            return True

        # Convert to local timezone for validation
        schedule_local = [dt.astimezone(self.timezone) for dt in schedule]

        for i, dt in enumerate(schedule_local):
            # Check hour is within valid range
            if dt.hour < self.start_hour or dt.hour > self.end_hour:
                raise ValueError(
                    f"Video {i+1} scheduled at {dt.hour}:00, outside allowed range "
                    f"({self.start_hour}:00 - {self.end_hour}:00)"
                )

            # Check interval between consecutive videos on same day
            if i > 0:
                prev_dt = schedule_local[i - 1]
                if prev_dt.date() == dt.date():
                    # Same day - check interval
                    time_diff = (dt - prev_dt).total_seconds() / 3600
                    if abs(time_diff - self.interval_hours) > 0.1:  # Allow small float errors
                        raise ValueError(
                            f"Video {i+1} interval is {time_diff:.1f}h, expected {self.interval_hours}h"
                        )

        logger.debug(f"Schedule validation passed for {len(schedule)} videos")
        return True

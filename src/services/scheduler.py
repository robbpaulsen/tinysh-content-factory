"""YouTube video scheduling service."""

import logging
from datetime import datetime, timedelta
from typing import List

import pytz

from src.config import settings

logger = logging.getLogger(__name__)


def parse_rfc3339_datetime(rfc3339_str: str) -> datetime:
    """
    Parse RFC 3339 datetime string to datetime object.

    YouTube API returns publishAt in format: 2025-11-15T12:00:00.000Z

    Args:
        rfc3339_str: RFC 3339 formatted datetime string

    Returns:
        datetime object in UTC
    """
    # Remove milliseconds and Z suffix, then parse
    dt_str = rfc3339_str.replace(".000Z", "").replace("Z", "")
    dt = datetime.fromisoformat(dt_str)
    # Ensure UTC timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    return dt


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

    def calculate_next_available_slot(
        self,
        existing_scheduled_videos: list[dict],
    ) -> datetime:
        """
        Calculate the next available time slot based on existing scheduled videos.

        This implements the "fill gaps" logic:
        - If there are gaps in today's schedule, fill them
        - If today is full (last slot at end_hour or later), start tomorrow
        - If no videos scheduled, start tomorrow at start_hour

        Args:
            existing_scheduled_videos: List of dicts with 'publishAt' (RFC 3339 string)

        Returns:
            Next available datetime in UTC
        """
        now_utc = datetime.now(pytz.UTC)
        now_local = now_utc.astimezone(self.timezone)

        # Parse existing scheduled times
        scheduled_times = []
        for video in existing_scheduled_videos:
            publish_at_str = video.get("publishAt")
            if publish_at_str:
                try:
                    dt_utc = parse_rfc3339_datetime(publish_at_str)
                    dt_local = dt_utc.astimezone(self.timezone)
                    scheduled_times.append(dt_local)
                except Exception as e:
                    logger.warning(f"Failed to parse publishAt: {publish_at_str} - {e}")

        # Sort scheduled times
        scheduled_times.sort()

        if not scheduled_times:
            # No videos scheduled - start tomorrow at start_hour
            logger.info("No scheduled videos found. Starting tomorrow at start_hour.")
            tomorrow = now_local + timedelta(days=1)
            next_slot = tomorrow.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
            return next_slot.astimezone(pytz.UTC)

        # Find the last scheduled video
        last_scheduled = scheduled_times[-1]
        logger.info(f"Last scheduled video: {last_scheduled.strftime('%Y-%m-%d %H:%M')}")

        # Check if last scheduled is today
        if last_scheduled.date() == now_local.date():
            # There are videos scheduled for today
            # Find next available slot for today
            current_hour = last_scheduled.hour + self.interval_hours

            if current_hour <= self.end_hour:
                # There's still a slot available today
                next_slot = last_scheduled.replace(hour=current_hour, minute=0, second=0, microsecond=0)
                logger.info(f"Next slot available today: {next_slot.strftime('%Y-%m-%d %H:%M')}")
                return next_slot.astimezone(pytz.UTC)
            else:
                # Today is full, move to tomorrow
                logger.info("Today's schedule is full. Moving to tomorrow.")
                next_day = last_scheduled + timedelta(days=1)
                next_slot = next_day.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
                return next_slot.astimezone(pytz.UTC)
        else:
            # Last scheduled video is in the future (not today)
            # Check if we can fill gaps in between

            # Find all days with scheduled videos
            scheduled_dates = sorted(set(dt.date() for dt in scheduled_times))

            # Check each day for gaps
            for date in scheduled_dates:
                # Get all scheduled times for this day
                day_schedule = [dt for dt in scheduled_times if dt.date() == date]
                day_schedule.sort()

                # Find gaps in this day's schedule
                expected_hour = self.start_hour
                for scheduled_dt in day_schedule:
                    if scheduled_dt.hour > expected_hour:
                        # Found a gap!
                        gap_slot = scheduled_dt.replace(hour=expected_hour, minute=0, second=0, microsecond=0)
                        logger.info(f"Found gap to fill: {gap_slot.strftime('%Y-%m-%d %H:%M')}")
                        return gap_slot.astimezone(pytz.UTC)
                    expected_hour = scheduled_dt.hour + self.interval_hours

                # Check if there's room at the end of this day
                last_hour_of_day = day_schedule[-1].hour
                if last_hour_of_day + self.interval_hours <= self.end_hour:
                    # There's a slot at the end of this day
                    end_slot = day_schedule[-1].replace(
                        hour=last_hour_of_day + self.interval_hours,
                        minute=0,
                        second=0,
                        microsecond=0
                    )
                    logger.info(f"Slot available at end of day: {end_slot.strftime('%Y-%m-%d %H:%M')}")
                    return end_slot.astimezone(pytz.UTC)

            # No gaps found - schedule after the last scheduled video
            next_day = last_scheduled + timedelta(days=1)
            next_slot = next_day.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
            logger.info(f"No gaps found. Next slot: {next_slot.strftime('%Y-%m-%d %H:%M')}")
            return next_slot.astimezone(pytz.UTC)

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
            start_date: Start date (default: earliest available slot starting today)

        Returns:
            List of datetime objects in UTC for each video publish time
        """
        if video_count <= 0:
            return []

        # Default start: calculate earliest possible slot from now
        if start_date is None:
            now_local = datetime.now(self.timezone)
            
            # If current time is before start_hour today, start today at start_hour
            if now_local.hour < self.start_hour:
                start_date = now_local.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
            
            # If current time is past end_hour today, start tomorrow at start_hour
            elif now_local.hour >= self.end_hour:
                start_date = (now_local + timedelta(days=1)).replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
            
            # If current time is within the window, find next interval slot
            else:
                # Find next slot that respects interval
                # E.g., if start=6, interval=2, now=9:30 -> next is 10:00
                # E.g., if start=6, interval=2, now=10:30 -> next is 12:00
                
                # Calculate hours since start_hour
                hours_since_start = now_local.hour - self.start_hour
                intervals_passed = hours_since_start // self.interval_hours
                
                next_interval_hour = self.start_hour + ((intervals_passed + 1) * self.interval_hours)
                
                if next_interval_hour <= self.end_hour:
                    start_date = now_local.replace(hour=next_interval_hour, minute=0, second=0, microsecond=0)
                else:
                    # No more slots today, start tomorrow
                    start_date = (now_local + timedelta(days=1)).replace(hour=self.start_hour, minute=0, second=0, microsecond=0)

        elif start_date.tzinfo is None:
            # If naive datetime, localize to configured timezone
            start_date = self.timezone.localize(start_date)
        else:
            # If aware datetime, convert to configured timezone
            start_date = start_date.astimezone(self.timezone)

        # Ensure start time is valid
        if start_date.hour < self.start_hour:
            start_date = start_date.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
        elif start_date.hour > self.end_hour:
            # If after end hour, move to next day
            start_date = start_date + timedelta(days=1)
            start_date = start_date.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
        
        # Adjust minute/second to 0
        start_date = start_date.replace(minute=0, second=0, microsecond=0)

        schedule = []
        current_date = start_date

        for i in range(video_count):
            # Calculate slot within the day
            # We can't just use i % slots_per_day because we might start in the middle of the day
            
            # If current time exceeds end_hour, move to next day
            if current_date.hour > self.end_hour:
                current_date = current_date + timedelta(days=1)
                current_date = current_date.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
            
            # Add to schedule
            publish_time_utc = current_date.astimezone(pytz.UTC)
            schedule.append(publish_time_utc)
            
            # Calculate next slot
            current_date = current_date + timedelta(hours=self.interval_hours)

        logger.info(f"Generated schedule for {video_count} videos")
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

        This implements smarter "fill gaps" logic:
        - Generates all potential slots for the next 30 days
        - Filters for slots in the future (from now)
        - Finds the first potential slot that isn't already occupied
        - Prioritizes filling gaps in today's schedule

        Args:
            existing_scheduled_videos: List of dicts with 'publishAt' (RFC 3339 string)

        Returns:
            Next available datetime in UTC
        """
        now_utc = datetime.now(pytz.UTC)
        now_local = now_utc.astimezone(self.timezone)

        # Determine the earliest time a slot can be considered valid
        # Add a small buffer (5 mins) to avoid scheduling in the immediate past
        earliest_valid_time = now_local.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=5)

        # Parse existing scheduled times and convert to local timezone
        # Use a set for faster O(1) lookups
        scheduled_times_local = set()
        for video in existing_scheduled_videos:
            publish_at_str = video.get("publishAt")
            if publish_at_str:
                try:
                    dt_utc = parse_rfc3339_datetime(publish_at_str)
                    dt_local = dt_utc.astimezone(self.timezone)
                    # Normalize to hour/minute 0 for comparison
                    scheduled_times_local.add(dt_local.replace(minute=0, second=0, microsecond=0))
                except Exception as e:
                    logger.warning(f"Failed to parse publishAt: {publish_at_str} - {e}")

        # Generate potential slots for the next 30 days
        # This approach ensures we systematically find the first available gap
        potential_slots = []
        
        # Start checking from today
        current_day = now_local.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
        
        for day_offset in range(30): # Check next 30 days
            check_date = current_day + timedelta(days=day_offset)
            
            # Generate slots for this day
            # From start_hour to end_hour with interval
            current_slot = check_date.replace(hour=self.start_hour)
            
            while current_slot.hour <= self.end_hour:
                # Only add if it respects end_hour (safety check loop condition)
                if current_slot.hour <= self.end_hour:
                    potential_slots.append(current_slot)
                
                current_slot += timedelta(hours=self.interval_hours)
                
                # Break if we wrapped around to next day (shouldn't happen with logic above but safe)
                if current_slot.date() != check_date.date():
                    break

        # Sort slots to ensure we pick earliest (should already be sorted by generation order)
        potential_slots.sort()

        # Find the first slot that:
        # 1. Is in the future (after earliest_valid_time)
        # 2. Is NOT in the set of already scheduled times
        for slot in potential_slots:
            if slot >= earliest_valid_time and slot not in scheduled_times_local:
                logger.info(f"Found available slot: {slot.strftime('%Y-%m-%d %H:%M')}")
                return slot.astimezone(pytz.UTC)

        # Fallback if no slots found in 30 days (extremely unlikely)
        logger.warning("No available slots found in next 30 days. Using fallback calculation.")
        
        if scheduled_times_local:
            last_scheduled = max(scheduled_times_local)
            next_slot = last_scheduled + timedelta(hours=self.interval_hours)
            
            # Adjust if outside daily hours
            if next_slot.hour > self.end_hour:
                next_slot = (next_slot + timedelta(days=1)).replace(hour=self.start_hour)
            elif next_slot.hour < self.start_hour:
                next_slot = next_slot.replace(hour=self.start_hour)
                
            return next_slot.astimezone(pytz.UTC)
        else:
            # Default to tomorrow start_hour if really nothing found
            tomorrow = (now_local + timedelta(days=1)).replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
            return tomorrow.astimezone(pytz.UTC)

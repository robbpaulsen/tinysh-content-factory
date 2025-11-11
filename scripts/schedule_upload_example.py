"""
Example script showing how to upload videos with scheduling.

This demonstrates uploading videos to YouTube with scheduled publish times.
Videos are uploaded as private and automatically published at the specified time.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from src.services.youtube import YouTubeService


async def upload_with_schedule_example():
    """Example: Upload video scheduled for 2 hours from now."""

    # Initialize YouTube service
    youtube = YouTubeService()

    # Set publish time (2 hours from now)
    publish_time = datetime.utcnow() + timedelta(hours=2)

    # Video details
    video_path = Path("output/video_001.mp4")
    title = "My Motivational Short"
    description = "An inspiring message about self-improvement. #motivation #shorts"
    tags = ["motivation", "shorts", "inspiration", "self-improvement"]

    print(f"Uploading video: {title}")
    print(f"Scheduled publish time: {publish_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    # Upload with scheduling
    result = youtube.upload_video(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        privacy_status="private",  # Required for scheduling
        publish_at=publish_time,  # Schedule publish time
    )

    print(f"✓ Video uploaded successfully!")
    print(f"  Video ID: {result.video_id}")
    print(f"  URL: {result.url}")
    print(f"  Status: Private (will publish at {publish_time.strftime('%Y-%m-%d %H:%M:%S')} UTC)")


async def upload_immediate_example():
    """Example: Upload video immediately as private (no scheduling)."""

    youtube = YouTubeService()

    video_path = Path("output/video_002.mp4")
    title = "Another Motivational Short"
    description = "More inspiration. #motivation #shorts"
    tags = ["motivation", "shorts"]

    print(f"Uploading video: {title}")
    print("Upload as private (no scheduling)")

    # Upload without scheduling (just private)
    result = youtube.upload_video(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        privacy_status="private",  # No publish_at = stays private until manual publish
    )

    print(f"✓ Video uploaded successfully!")
    print(f"  Video ID: {result.video_id}")
    print(f"  URL: {result.url}")
    print(f"  Status: Private (manual publish required)")


async def schedule_multiple_videos():
    """Example: Schedule multiple videos at different times."""

    youtube = YouTubeService()

    # Schedule 3 videos, one per day
    videos = [
        {
            "path": Path("output/video_001.mp4"),
            "title": "Day 1: Start Your Journey",
            "publish_in_hours": 24,  # Tomorrow
        },
        {
            "path": Path("output/video_002.mp4"),
            "title": "Day 2: Build Momentum",
            "publish_in_hours": 48,  # 2 days from now
        },
        {
            "path": Path("output/video_003.mp4"),
            "title": "Day 3: Stay Consistent",
            "publish_in_hours": 72,  # 3 days from now
        },
    ]

    for video_info in videos:
        publish_time = datetime.utcnow() + timedelta(hours=video_info["publish_in_hours"])

        print(f"\nUploading: {video_info['title']}")
        print(f"Scheduled for: {publish_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        result = youtube.upload_video(
            video_path=video_info["path"],
            title=video_info["title"],
            description="Daily motivation series. #motivation #shorts",
            tags=["motivation", "shorts", "daily"],
            publish_at=publish_time,
        )

        print(f"✓ Uploaded! URL: {result.url}")


if __name__ == "__main__":
    # Run one of the examples:

    # Example 1: Upload with 2-hour schedule
    asyncio.run(upload_with_schedule_example())

    # Example 2: Upload as private without scheduling
    # asyncio.run(upload_immediate_example())

    # Example 3: Schedule multiple videos
    # asyncio.run(schedule_multiple_videos())

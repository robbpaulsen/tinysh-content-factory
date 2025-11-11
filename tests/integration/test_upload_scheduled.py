"""
Test script for scheduled YouTube upload workflow.

This script tests the complete flow:
1. Generate SEO metadata for videos without metadata
2. Upload videos as private with metadata
3. Schedule them for specific publish times

Usage:
    python tests/integration/test_upload_scheduled.py
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import pytz

from src.config import settings
from src.models import VideoScript, Scene
from src.services.seo_optimizer import SEOOptimizerService
from src.services.youtube import YouTubeService


async def generate_metadata_for_video(video_path: Path) -> dict:
    """
    Generate SEO metadata for a video without existing metadata.

    Args:
        video_path: Path to video file

    Returns:
        Dictionary with SEO metadata
    """
    print(f"\n📝 Generating metadata for: {video_path.name}")

    # Create a mock script for SEO generation
    # In real workflow, this comes from the video generation process
    mock_script = VideoScript(
        title="Motivational Short: Push Through Challenges",
        description="An inspiring message about overcoming obstacles and staying focused.",
        scenes=[
            Scene(
                text="Every challenge is an opportunity to grow stronger.",
                image_prompt="Motivational scene",
            )
        ],
    )

    # Initialize SEO optimizer
    seo_optimizer = SEOOptimizerService()

    # Generate SEO-optimized metadata
    metadata = await seo_optimizer.generate_seo_metadata(
        script=mock_script,
        profile_name="test_profile",
    )

    # Convert to dict for upload
    metadata_dict = {
        "title": metadata.title,
        "description": metadata.description,
        "tags": metadata.tags,
        "category_id": metadata.category_id,
    }

    # Save metadata to JSON file
    metadata_path = video_path.with_suffix("").name + "_metadata.json"
    metadata_file = video_path.parent / metadata_path

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata_dict, f, indent=2, ensure_ascii=False)

    print(f"✓ Metadata saved to: {metadata_file.name}")
    print(f"  Title: {metadata.title}")
    print(f"  Tags: {', '.join(metadata.tags[:3])}...")

    return metadata_dict


async def upload_with_schedule(
    video_path: Path,
    metadata: dict,
    publish_time: datetime,
) -> str:
    """
    Upload video as private with scheduled publish time.

    Args:
        video_path: Path to video file
        metadata: SEO metadata dictionary
        publish_time: Scheduled publish time (timezone-aware)

    Returns:
        YouTube video URL
    """
    print(f"\n📤 Uploading: {video_path.name}")

    # Initialize YouTube service
    youtube = YouTubeService()

    # Convert publish time to local timezone for display
    timezone = pytz.timezone(settings.youtube_timezone)
    publish_local = publish_time.astimezone(timezone)

    print(f"  Title: {metadata['title']}")
    print(f"  Schedule: {publish_local.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"  Privacy: private (scheduled)")

    # Upload with scheduling
    result = youtube.upload_video(
        video_path=video_path,
        title=metadata["title"],
        description=metadata["description"],
        tags=metadata["tags"],
        category_id=metadata["category_id"],
        privacy_status="private",  # Required for scheduling
        publish_at=publish_time,  # Scheduled publish time
    )

    print(f"✓ Uploaded successfully!")
    print(f"  Video ID: {result.video_id}")
    print(f"  URL: {result.url}")

    return result.url


async def test_two_video_upload():
    """
    Test uploading two videos with scheduled publish times.

    Schedule:
    - Video 1: Tomorrow at 6 AM
    - Video 2: Tomorrow at 8 PM
    """
    print("\n" + "=" * 60)
    print("🧪 Test: Upload 2 Videos with Scheduling")
    print("=" * 60)

    # Get video files from output directory
    output_dir = Path("output")
    video_files = sorted(output_dir.glob("video_*.mp4"))

    if len(video_files) < 2:
        print(f"\n❌ Error: Found only {len(video_files)} video(s) in output/")
        print("   Need at least 2 videos for this test")
        return

    # Use first 2 videos
    video1_path = video_files[0]
    video2_path = video_files[1]

    print(f"\nVideos to upload:")
    print(f"  1. {video1_path.name}")
    print(f"  2. {video2_path.name}")

    # Setup timezone
    timezone = pytz.timezone(settings.youtube_timezone)

    # Schedule times for tomorrow (November 12, 2025)
    tomorrow = datetime(2025, 11, 12, tzinfo=timezone)

    schedule_video1 = tomorrow.replace(hour=6, minute=0, second=0)   # 6 AM
    schedule_video2 = tomorrow.replace(hour=20, minute=0, second=0)  # 8 PM

    print(f"\nScheduled publish times ({settings.youtube_timezone}):")
    print(f"  Video 1: {schedule_video1.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Video 2: {schedule_video2.strftime('%Y-%m-%d %H:%M')}")

    # Convert to UTC for YouTube API
    schedule_video1_utc = schedule_video1.astimezone(pytz.UTC)
    schedule_video2_utc = schedule_video2.astimezone(pytz.UTC)

    try:
        # Step 1: Generate metadata for video 1
        print("\n" + "-" * 60)
        print("STEP 1: Generate Metadata")
        print("-" * 60)

        metadata1 = await generate_metadata_for_video(video1_path)
        metadata2 = await generate_metadata_for_video(video2_path)

        # Step 2: Upload videos with scheduling
        print("\n" + "-" * 60)
        print("STEP 2: Upload Videos with Scheduling")
        print("-" * 60)

        url1 = await upload_with_schedule(video1_path, metadata1, schedule_video1_utc)
        url2 = await upload_with_schedule(video2_path, metadata2, schedule_video2_utc)

        # Summary
        print("\n" + "=" * 60)
        print("✅ Test Complete!")
        print("=" * 60)
        print(f"\nResults:")
        print(f"  Video 1: {url1}")
        print(f"    Scheduled: {schedule_video1.strftime('%Y-%m-%d %H:%M %Z')}")
        print(f"\n  Video 2: {url2}")
        print(f"    Scheduled: {schedule_video2.strftime('%Y-%m-%d %H:%M %Z')}")
        print(f"\n📌 Verify in YouTube Studio:")
        print(f"   https://studio.youtube.com → Content → Videos")
        print(f"   Check that both videos show 'Scheduled' badge")
        print()

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_two_video_upload())

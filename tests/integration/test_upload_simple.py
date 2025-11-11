"""
Simplified test script for manual step-by-step upload.

This breaks down the workflow into individual steps for easier testing:
1. Generate metadata only
2. Upload with scheduling only

Usage:
    # Step 1: Generate metadata
    python tests/integration/test_upload_simple.py generate-metadata

    # Step 2: Upload with scheduling
    python tests/integration/test_upload_simple.py upload-scheduled
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import pytz

from src.config import settings
from src.models import VideoScript, Scene
from src.services.seo_optimizer import SEOOptimizerService
from src.services.youtube import YouTubeService


async def generate_metadata_only():
    """Generate metadata for videos without uploading."""
    print("\n📝 Generating metadata for videos in output/\n")

    output_dir = Path("output")
    video_files = sorted(output_dir.glob("video_*.mp4"))

    if not video_files:
        print("❌ No videos found in output/")
        return

    print(f"Found {len(video_files)} video(s)\n")

    seo_optimizer = SEOOptimizerService()

    for i, video_path in enumerate(video_files[:2], 1):  # Process first 2
        print(f"{i}. {video_path.name}")

        # Check if metadata already exists
        metadata_path = video_path.parent / f"{video_path.stem}_metadata.json"
        if metadata_path.exists():
            print(f"   ⚠ Metadata already exists, skipping...")
            continue

        # Create mock script for SEO
        mock_script = VideoScript(
            title=f"Motivational Short {i}: Daily Inspiration",
            description="Transform your mindset and achieve your goals with this powerful message.",
            scenes=[
                Scene(
                    text="Believe in yourself and push through every challenge.",
                    image_prompt="Motivational scene",
                )
            ],
        )

        # Generate SEO metadata
        metadata = await seo_optimizer.generate_seo_metadata(
            video_title=mock_script.title,
            video_description=mock_script.description,
            script_text=mock_script.scenes[0].text,
            profile_name="default",
        )

        # Save to JSON
        metadata_dict = {
            "title": metadata.title,
            "description": metadata.description,
            "tags": metadata.tags,
            "category_id": metadata.category_id,
        }

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata_dict, f, indent=2, ensure_ascii=False)

        print(f"   ✓ Saved: {metadata_path.name}")
        print(f"   Title: {metadata.title}")
        print()

    print("✅ Metadata generation complete!\n")


async def upload_scheduled_only():
    """Upload videos with metadata using scheduled publish times."""
    print("\n📤 Uploading videos with scheduling\n")

    output_dir = Path("output")
    video_files = sorted(output_dir.glob("video_*.mp4"))[:2]  # First 2 videos

    if len(video_files) < 2:
        print(f"❌ Need at least 2 videos, found {len(video_files)}")
        return

    # Setup schedule times
    timezone = pytz.timezone(settings.youtube_timezone)
    tomorrow = datetime(2025, 11, 12, tzinfo=timezone)

    schedules = [
        tomorrow.replace(hour=6, minute=0, second=0),   # 6 AM
        tomorrow.replace(hour=20, minute=0, second=0),  # 8 PM
    ]

    youtube = YouTubeService()

    print(f"Schedule ({settings.youtube_timezone}):")
    for i, schedule in enumerate(schedules, 1):
        print(f"  Video {i}: {schedule.strftime('%Y-%m-%d %H:%M')}")
    print()

    results = []

    for i, (video_path, schedule_time) in enumerate(zip(video_files, schedules), 1):
        print(f"{i}. Uploading: {video_path.name}")

        # Load metadata
        metadata_path = video_path.parent / f"{video_path.stem}_metadata.json"

        if not metadata_path.exists():
            print(f"   ❌ Error: No metadata file found!")
            print(f"   Run: python tests/integration/test_upload_simple.py generate-metadata")
            continue

        with open(metadata_path, encoding="utf-8") as f:
            metadata = json.load(f)

        # Convert to UTC for YouTube API
        schedule_utc = schedule_time.astimezone(pytz.UTC)

        # Upload
        try:
            result = youtube.upload_video(
                video_path=video_path,
                title=metadata["title"],
                description=metadata["description"],
                tags=metadata["tags"],
                category_id=metadata["category_id"],
                privacy_status="private",
                publish_at=schedule_utc,
            )

            print(f"   ✓ Uploaded: {result.url}")
            print(f"   Scheduled: {schedule_time.strftime('%Y-%m-%d %H:%M %Z')}")
            results.append((video_path.name, result.url, schedule_time))

        except Exception as e:
            print(f"   ❌ Error: {e}")

        print()

    # Summary
    if results:
        print("=" * 60)
        print("✅ Upload Complete!")
        print("=" * 60)
        for name, url, schedule in results:
            print(f"\n{name}")
            print(f"  URL: {url}")
            print(f"  Scheduled: {schedule.strftime('%Y-%m-%d %H:%M %Z')}")
        print()


def show_usage():
    """Show usage instructions."""
    print("\nUsage:")
    print("  python tests/integration/test_upload_simple.py generate-metadata")
    print("  python tests/integration/test_upload_simple.py upload-scheduled")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_usage()
        sys.exit(1)

    command = sys.argv[1]

    if command == "generate-metadata":
        asyncio.run(generate_metadata_only())
    elif command == "upload-scheduled":
        asyncio.run(upload_scheduled_only())
    else:
        print(f"\n❌ Unknown command: {command}")
        show_usage()
        sys.exit(1)

"""Test local video merging - Concatenate multiple videos"""

import asyncio
import sys
from pathlib import Path


async def test_video_merge_local():
    """Test video merging in local mode"""
    print("\n" + "="*60)
    print("TEST: Video Merge - Local Mode")
    print("="*60)

    try:
        from src.services.media import MediaService
        from PIL import Image
        import io

        # Initialize in local mode
        print("\n[1/5] Initializing MediaService in LOCAL mode...")
        media_service = MediaService(execution_mode="local")
        print("✓ MediaService initialized")

        # Step 1: Generate 2 test videos
        print("\n[2/5] Generating 2 test videos...")
        video_ids = []

        for i in range(2):
            print(f"\n  Generating video {i+1}/2...")

            # Generate TTS
            text = f"This is video number {i+1}. It contains test content for merging."
            voice_config = {
                "engine": "kokoro",
                "voice": "af_bella",
                "speed": 1.0
            }

            tts_file_id = await media_service.generate_tts_direct(text, voice_config)
            print(f"    ✓ TTS generated: {tts_file_id}")

            # Create test image with different color for each video
            colors = ['#1a1a2e', '#2e1a1a', '#1a2e1a']
            img = Image.new('RGB', (1080, 1920), color=colors[i])

            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            from src.media_local.storage.manager import MediaType
            image_file_id = media_service._local_storage.upload_media(
                MediaType.IMAGE,
                img_bytes.getvalue(),
                ".png"
            )
            print(f"    ✓ Image created: {image_file_id}")

            # Generate video
            video_file_id = await media_service.start_captioned_video_generation(
                image_id=image_file_id,
                tts_id=tts_file_id,
                text=text,
                subtitle_config={
                    "font_size": 32,
                    "color": "#FFFFFF",
                    "bold": True
                }
            )
            print(f"    ✓ Video {i+1} generated: {video_file_id}")
            video_ids.append(video_file_id)

        # Step 2: Merge videos
        print(f"\n[3/5] Merging {len(video_ids)} videos...")
        print("  Please wait...")

        merged_video_id = await media_service.merge_videos(
            video_ids=video_ids,
            background_music_id=None,  # No background music for this test
            music_volume=None
        )
        print(f"✓ Videos merged: {merged_video_id}")

        # Step 3: Verify merged video
        print("\n[4/5] Verifying merged video...")
        merged_path = media_service._local_storage.get_media_path(merged_video_id)

        if Path(merged_path).exists():
            file_size = Path(merged_path).stat().st_size
            print(f"✓ Merged video exists: {merged_path}")
            print(f"✓ File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")

            # Verify merged video is larger than individual videos
            video1_path = media_service._local_storage.get_media_path(video_ids[0])
            video1_size = Path(video1_path).stat().st_size

            if file_size < video1_size:
                print("⚠ Warning: Merged video is smaller than individual videos")
                return False

            print(f"✓ Merged video size validation passed")
        else:
            print(f"✗ Merged video not found: {merged_path}")
            return False

        # Cleanup
        print("\n[5/5] Cleaning up...")
        await media_service.close()
        print("✓ Service closed")

        print("\n" + "="*60)
        print("✓ VIDEO MERGE TEST PASSED")
        print("="*60)
        print("\n📊 Result:")
        print(f"   - Mode: Local (no Docker)")
        print(f"   - Videos merged: {len(video_ids)}")
        print(f"   - Output: {merged_video_id}")
        print(f"   - Size: {file_size/1024/1024:.2f} MB")
        print("\n🎉 Local video merging is working!")

        return True

    except Exception as e:
        print(f"\n✗ Video merge test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run video merge test"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  VIDEO MERGE - LOCAL MODE TEST".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)

    print("\n⏱ NOTE: This test generates 2 videos then merges them")
    print("         May take 2-3 minutes to complete\n")

    success = await test_video_merge_local()

    if success:
        print("\n✅ RESULT: PASS - Local video merging ready!")
        return 0
    else:
        print("\n❌ RESULT: FAIL - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

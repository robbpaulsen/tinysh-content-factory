"""Test local video generation - Captioned videos"""

import asyncio
import sys
from pathlib import Path


async def test_captioned_video_local():
    """Test captioned video generation in local mode"""
    print("\n" + "="*60)
    print("TEST: Captioned Video Generation - Local Mode")
    print("="*60)

    try:
        from src.services.media import MediaService
        from PIL import Image
        import io

        # Initialize in local mode
        print("\n[1/6] Initializing MediaService in LOCAL mode...")
        media_service = MediaService(execution_mode="local")
        print("✓ MediaService initialized")

        # Step 1: Generate TTS
        text = "This is a test video with captions. The quick brown fox jumps over the lazy dog."
        print(f"\n[2/6] Generating TTS...")
        print(f"  Text: '{text}'")

        voice_config = {
            "engine": "kokoro",
            "voice": "af_bella",
            "speed": 1.0
        }

        tts_file_id = await media_service.generate_tts_direct(text, voice_config)
        print(f"✓ TTS generated: {tts_file_id}")

        # Step 2: Create a test image (solid color background)
        print("\n[3/6] Creating test image...")
        img_width = 1080
        img_height = 1920
        img = Image.new('RGB', (img_width, img_height), color='#1a1a2e')

        # Save image to temporary file
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        # Upload image to storage
        from src.media_local.storage.manager import MediaType
        image_file_id = media_service._local_storage.upload_media(
            MediaType.IMAGE,
            img_bytes.getvalue(),
            ".png"
        )
        print(f"✓ Test image created: {image_file_id}")

        # Step 3: Generate captioned video
        print("\n[4/6] Generating captioned video...")
        print("  This may take 30-60 seconds...")

        subtitle_config = {
            "font_size": 32,
            "color": "#FFFFFF",
            "font": "Arial",
            "bold": True,
            "outline_color": "#000000",
            "outline_width": 3,
            "alignment": 2  # Bottom
        }

        video_file_id = await media_service.start_captioned_video_generation(
            image_id=image_file_id,
            tts_id=tts_file_id,
            text=text,
            subtitle_config=subtitle_config
        )
        print(f"✓ Video generated: {video_file_id}")

        # Step 4: Verify video file exists
        print("\n[5/6] Verifying generated video...")
        video_path = media_service._local_storage.get_media_path(video_file_id)

        if Path(video_path).exists():
            file_size = Path(video_path).stat().st_size
            print(f"✓ Video file exists: {video_path}")
            print(f"✓ File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")

            # Basic validation
            if file_size < 50000:  # Less than 50KB is suspicious for a video
                print("⚠ Warning: Video file size seems too small")
                return False
        else:
            print(f"✗ Video file not found: {video_path}")
            return False

        # Cleanup
        print("\n[6/6] Cleaning up...")
        await media_service.close()
        print("✓ Service closed")

        print("\n" + "="*60)
        print("✓ CAPTIONED VIDEO TEST PASSED")
        print("="*60)
        print("\n📊 Result:")
        print(f"   - Mode: Local (no Docker)")
        print(f"   - TTS: {tts_file_id}")
        print(f"   - Image: {image_file_id}")
        print(f"   - Video: {video_file_id}")
        print(f"   - Size: {file_size/1024/1024:.2f} MB")
        print("\n🎉 Local video generation is working!")

        return True

    except Exception as e:
        print(f"\n✗ Captioned video test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run captioned video test"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  VIDEO GENERATION - LOCAL MODE TEST".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)

    print("\n⏱ NOTE: Video generation using GPU (NVENC) if available")
    print("         First run may take longer due to model loading\n")

    success = await test_captioned_video_local()

    if success:
        print("\n✅ RESULT: PASS - Local video generation ready!")
        return 0
    else:
        print("\n❌ RESULT: FAIL - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

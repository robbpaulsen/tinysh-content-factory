"""Test Chatterbox TTS in local mode via MediaService"""

import asyncio
import sys
from pathlib import Path


async def test_chatterbox_via_mediaservice():
    """Test Chatterbox TTS through MediaService local mode"""
    print("\n" + "="*60)
    print("TEST: Chatterbox TTS - Via MediaService Local Mode")
    print("="*60)

    try:
        from src.services.media import MediaService

        # Initialize in local mode
        print("\n[1/5] Initializing MediaService in LOCAL mode...")
        media_service = MediaService(execution_mode="local")
        print("✓ MediaService initialized")

        # Test Chatterbox TTS
        text = "This is a test of Chatterbox text to speech in local mode."
        print(f"\n[2/5] Generating TTS with Chatterbox...")
        print(f"  Text: '{text}'")
        print("  Please wait, first run may take 30-60 seconds...")

        # Create voice config for Chatterbox
        voice_config = {
            "engine": "chatterbox",
            "exaggeration": 0.5,
            "cfg_weight": 0.5,
            "temperature": 0.7,
            "sample_path": None  # No voice cloning for this test
        }

        file_id = await media_service.generate_tts_direct(text, voice_config)
        print(f"\n[3/5] ✓ TTS generated: {file_id}")

        # Verify file exists
        print("\n[4/5] Verifying generated file...")
        file_path = media_service._local_storage.get_media_path(file_id)

        if Path(file_path).exists():
            file_size = Path(file_path).stat().st_size
            print(f"✓ File exists: {file_path}")
            print(f"✓ File size: {file_size:,} bytes ({file_size/1024:.2f} KB)")

            # Basic validation
            if file_size < 1000:
                print("⚠ Warning: File size seems too small")
                return False
        else:
            print(f"✗ File not found: {file_path}")
            return False

        # Cleanup
        print("\n[5/5] Cleaning up...")
        await media_service.close()
        print("✓ Service closed")

        print("\n" + "="*60)
        print("✓ CHATTERBOX TTS TEST PASSED")
        print("="*60)
        print("\n📊 Result:")
        print(f"   - Engine: Chatterbox")
        print(f"   - Mode: Local (no Docker)")
        print(f"   - File: {file_id}")
        print(f"   - Size: {file_size/1024:.2f} KB")
        print("\n🎉 Chatterbox is working locally!")

        return True

    except Exception as e:
        print(f"\n✗ Chatterbox test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run Chatterbox test"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  CHATTERBOX TTS - LOCAL MODE TEST".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)

    print("\n⏱ NOTE: First run downloads model (~1-2 GB)")
    print("         Subsequent runs will be much faster\n")

    success = await test_chatterbox_via_mediaservice()

    if success:
        print("\n✅ RESULT: PASS - Chatterbox is ready for production!")
        return 0
    else:
        print("\n❌ RESULT: FAIL - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

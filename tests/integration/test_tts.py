"""Simple test script to verify TTS fix."""

import asyncio
import logging
from src.services.media import MediaService

# Enable debug logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """Test TTS generation with the fix."""
    print("=" * 80)
    print("Testing TTS Generation Fix")
    print("=" * 80)

    media_service = MediaService()

    try:
        # Test 1: Simple TTS generation
        print("\n[Test 1] Generating TTS with Chatterbox...")
        text = "This is a test of the text to speech system."
        file_id = await media_service.generate_tts_direct(text)
        print(f"✅ SUCCESS! Generated TTS with file_id: {file_id}")

        # Test 2: Health check
        print("\n[Test 2] Media server health check...")
        is_healthy = await media_service.health_check()
        print(f"✅ Media server is healthy: {is_healthy}")

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await media_service.close()

    print("\n" + "=" * 80)
    print("Test completed")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())

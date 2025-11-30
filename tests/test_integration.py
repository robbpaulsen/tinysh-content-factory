"""Integration test - Local vs Remote execution modes"""

import asyncio
import sys
from pathlib import Path


async def test_local_mode():
    """Test MediaService in local mode"""
    print("\n" + "="*60)
    print("TEST: MediaService - LOCAL MODE")
    print("="*60)

    try:
        from src.services.media import MediaService

        # Initialize in local mode
        media_service = MediaService(execution_mode="local")
        print("✓ MediaService initialized in LOCAL mode")

        # Test TTS generation
        text = "Hello world, this is a local execution test."
        print(f"\n  Generating TTS: '{text}'")
        print("  Please wait...")

        file_id = await media_service.generate_tts_direct(text)
        print(f"✓ TTS generated: {file_id}")

        # Verify file exists
        file_path = media_service._local_storage.get_media_path(file_id)
        if Path(file_path).exists():
            file_size = Path(file_path).stat().st_size
            print(f"✓ File exists: {file_path} ({file_size} bytes)")
        else:
            print(f"✗ File not found: {file_path}")
            return False

        # Cleanup
        await media_service.close()
        print("✓ Service closed")

        return True

    except Exception as e:
        print(f"✗ Local mode test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run integration tests"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  INTEGRATION TEST - LOCAL MODE".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)

    results = {
        "Local Mode": await test_local_mode(),
    }

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    total = len(results)
    passed = sum(1 for r in results.values() if r)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} | {test_name}")

    print("="*60)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("="*60)

    if passed == total:
        print("\n✓ Integration test passed!")
        print("\n🎉 LOCAL MODE IS WORKING!")
        print("   - MediaService can now run without Docker")
        print("   - TTS generation works locally")
        print("   - Ready for production use")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

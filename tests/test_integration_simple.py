"""Simple integration test - Verify local mode initialization only"""

import sys


def test_local_mode_init():
    """Test MediaService initialization in local mode (no TTS execution)"""
    print("\n" + "="*60)
    print("TEST: MediaService Local Mode - Initialization Only")
    print("="*60)

    try:
        from src.services.media import MediaService

        # Test 1: Initialize in local mode
        print("\n[1/4] Initializing MediaService in LOCAL mode...")
        media_service = MediaService(execution_mode="local")
        print("✓ MediaService initialized")

        # Test 2: Verify mode
        print("\n[2/4] Verifying execution mode...")
        assert media_service.execution_mode == "local", "Wrong execution mode!"
        print(f"✓ Execution mode: {media_service.execution_mode}")

        # Test 3: Verify local components initialized
        print("\n[3/4] Checking local components...")
        assert media_service._local_storage is not None, "Storage not initialized!"
        assert media_service._local_media_utils is not None, "MediaUtils not initialized!"
        assert media_service._local_caption is not None, "Caption not initialized!"
        print("✓ Storage Manager initialized")
        print("✓ MediaUtils (FFmpeg) initialized")
        print("✓ Caption Generator initialized")

        # Test 4: Verify TTS engines are lazy-loaded (not initialized yet)
        print("\n[4/4] Verifying TTS lazy loading...")
        assert media_service._local_kokoro_tts is None, "Kokoro should be lazy-loaded!"
        assert media_service._local_chatterbox_tts is None, "Chatterbox should be lazy-loaded!"
        print("✓ TTS engines are lazy-loaded (will load on first use)")

        print("\n" + "="*60)
        print("✓ ALL INITIALIZATION TESTS PASSED")
        print("="*60)
        print("\n📊 Summary:")
        print("   - LOCAL mode is properly configured")
        print("   - Core modules loaded successfully")
        print("   - TTS engines ready (lazy-load)")
        print("   - System ready for local execution")
        print("\n🎉 Integration successful - Docker not required!")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run simple integration test"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  INTEGRATION - LOCAL MODE VERIFICATION".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)

    success = test_local_mode_init()

    if success:
        print("\n✅ RESULT: PASS")
        return 0
    else:
        print("\n❌ RESULT: FAIL")
        return 1


if __name__ == "__main__":
    sys.exit(main())

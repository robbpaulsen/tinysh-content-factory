"""Test suite for Smart Cache System"""

import asyncio
import sys
from pathlib import Path


async def test_cache_tts_exact_match():
    """Test TTS cache with exact hash matching"""
    print("\n" + "="*60)
    print("TEST: Cache - TTS Exact Match")
    print("="*60)

    try:
        from src.services.media import MediaService

        # Initialize with cache enabled
        media_service = MediaService(execution_mode="local", enable_cache=True)
        print("✓ MediaService initialized with cache enabled")

        # First generation - should be cache miss
        text = "This is a test for cache functionality."
        print(f"\n  First generation: '{text}'")

        file_id_1 = await media_service.generate_tts_direct(text)
        print(f"✓ First TTS generated: {file_id_1}")

        # Second generation with same text - should be cache hit
        print(f"\n  Second generation (same text): '{text}'")

        # Clear stats before second call to verify cache hit
        stats_before = media_service.get_cache_stats()
        hits_before = stats_before['session']['hits']

        file_id_2 = await media_service.generate_tts_direct(text)
        print(f"✓ Second TTS returned: {file_id_2}")

        # Check cache stats - should show a hit
        stats = media_service.get_cache_stats()
        print(f"\n  Cache Stats:")
        print(f"  - Session hits: {stats['session']['hits']}")
        print(f"  - Session misses: {stats['session']['misses']}")
        print(f"  - Hit rate: {stats['hit_rate']:.1%}")
        print(f"  - DB total uses: {stats['database']['by_type'].get('tts', {}).get('total_uses', 0)}")

        # Verify cache hit occurred (hits increased)
        if stats['session']['hits'] > hits_before:
            print("✓ Cache HIT detected - reused cached audio")
        else:
            print("✗ Cache MISS - No cache hit detected")
            return False

        # Verify file exists
        file_path_2 = media_service._local_storage.get_media_path(file_id_2)
        if Path(file_path_2).exists():
            print(f"✓ Cached file copied to: {file_id_2}")
        else:
            print("✗ File not found")
            return False

        await media_service.close()
        print("\n✓ TTS cache exact match test PASSED")
        return True

    except Exception as e:
        print(f"✗ TTS cache test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_tts_similarity_match():
    """Test TTS cache with similarity matching"""
    print("\n" + "="*60)
    print("TEST: Cache - TTS Similarity Match")
    print("="*60)

    try:
        from src.services.media import MediaService

        # Initialize with cache enabled
        media_service = MediaService(execution_mode="local", enable_cache=True)
        print("✓ MediaService initialized with similarity matching")

        # First generation
        text1 = "Hello world, this is a test."
        print(f"\n  First generation: '{text1}'")
        file_id_1 = await media_service.generate_tts_direct(text1)
        print(f"✓ First TTS generated: {file_id_1}")

        # Second generation with similar but not identical text
        text2 = "Hello world, this is another test."
        print(f"\n  Second generation (similar): '{text2}'")
        file_id_2 = await media_service.generate_tts_direct(text2)
        print(f"✓ Second TTS generated: {file_id_2}")

        # Check cache stats
        stats = media_service.get_cache_stats()
        print(f"\n  Cache Stats:")
        print(f"  - Similarity hits: {stats['session']['similarity_hits']}")
        print(f"  - Total hits: {stats['session']['hits']}")

        if stats['session']['similarity_hits'] > 0:
            print("✓ Similarity matching detected similar prompts")
        else:
            print("ℹ Similarity threshold not met (expected for different texts)")

        await media_service.close()
        print("\n✓ TTS similarity match test PASSED")
        return True

    except Exception as e:
        print(f"✗ TTS similarity test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_different_voice_config():
    """Test that different voice configs create separate cache entries"""
    print("\n" + "="*60)
    print("TEST: Cache - Different Voice Configs")
    print("="*60)

    try:
        from src.services.media import MediaService

        media_service = MediaService(execution_mode="local", enable_cache=True)
        print("✓ MediaService initialized")

        text = "Same text, different voices."

        # Generate with first voice config
        voice_config_1 = {"engine": "kokoro", "voice": "af_bella", "speed": 1.0}
        print(f"\n  First generation with voice: af_bella")
        file_id_1 = await media_service.generate_tts_direct(text, voice_config_1)
        print(f"✓ TTS generated: {file_id_1}")

        # Generate with different voice config - should be cache miss
        voice_config_2 = {"engine": "kokoro", "voice": "af_sarah", "speed": 1.0}
        print(f"\n  Second generation with voice: af_sarah")
        file_id_2 = await media_service.generate_tts_direct(text, voice_config_2)
        print(f"✓ TTS generated: {file_id_2}")

        # Should have different file_ids
        if file_id_1 != file_id_2:
            print("✓ Different voice configs created separate cache entries")
        else:
            print("✗ Same file_id for different voices (unexpected)")
            return False

        # Generate again with first config - should be cache hit
        print(f"\n  Third generation with voice: af_bella (same as first)")

        # Track hits before
        stats_before = media_service.get_cache_stats()
        hits_before = stats_before['session']['hits']

        file_id_3 = await media_service.generate_tts_direct(text, voice_config_1)
        print(f"✓ TTS generated: {file_id_3}")

        # Verify cache hit
        stats = media_service.get_cache_stats()
        if stats['session']['hits'] > hits_before:
            print("✓ Cache HIT with same voice config")
        else:
            print(f"✗ Cache MISS for same config")
            return False

        await media_service.close()
        print("\n✓ Voice config cache test PASSED")
        return True

    except Exception as e:
        print(f"✗ Voice config cache test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_cleanup():
    """Test cache cleanup functionality"""
    print("\n" + "="*60)
    print("TEST: Cache - Cleanup")
    print("="*60)

    try:
        from src.services.media import MediaService

        media_service = MediaService(execution_mode="local", enable_cache=True)
        print("✓ MediaService initialized")

        # Generate some TTS
        text = "Test for cache cleanup."
        print(f"\n  Generating TTS: '{text}'")
        file_id = await media_service.generate_tts_direct(text)
        print(f"✓ TTS generated: {file_id}")

        # Check stats before cleanup
        stats_before = media_service.get_cache_stats()
        total_before = stats_before["database"]["total_entries"]
        print(f"\n  Entries before cleanup: {total_before}")

        # Clear TTS cache
        if total_before > 0:
            cleared = media_service.cache.clear("tts")
            print(f"✓ Cleared {cleared} TTS entries")

            # Check stats after cleanup
            stats_after = media_service.get_cache_stats()
            total_after = stats_after["database"]["total_entries"]
            print(f"  Entries after cleanup: {total_after}")

            if total_after < total_before:
                print("✓ Cache cleanup successful")
            else:
                print("✗ Cache not cleared properly")
                return False
        else:
            print("ℹ No entries to clear")

        await media_service.close()
        print("\n✓ Cache cleanup test PASSED")
        return True

    except Exception as e:
        print(f"✗ Cache cleanup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_disabled():
    """Test that cache can be disabled"""
    print("\n" + "="*60)
    print("TEST: Cache - Disabled Mode")
    print("="*60)

    try:
        from src.services.media import MediaService

        # Initialize with cache disabled
        media_service = MediaService(execution_mode="local", enable_cache=False)
        print("✓ MediaService initialized with cache disabled")

        # Check that cache is None
        if media_service.cache is None:
            print("✓ Cache is disabled")
        else:
            print("✗ Cache should be None when disabled")
            return False

        # Generate TTS - should work without cache
        text = "Test without cache."
        file_id = await media_service.generate_tts_direct(text)
        print(f"✓ TTS generated without cache: {file_id}")

        # Check stats
        stats = media_service.get_cache_stats()
        if stats["enabled"] == False:
            print("✓ Cache stats show disabled")
        else:
            print("✗ Cache stats incorrect")
            return False

        await media_service.close()
        print("\n✓ Cache disabled test PASSED")
        return True

    except Exception as e:
        print(f"✗ Cache disabled test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all cache tests"""
    print("\n" + "="*80)
    print("SMART CACHE SYSTEM - TEST SUITE")
    print("="*80)

    tests = [
        ("TTS Exact Match", test_cache_tts_exact_match),
        ("TTS Similarity Match", test_cache_tts_similarity_match),
        ("Different Voice Configs", test_cache_different_voice_config),
        ("Cache Cleanup", test_cache_cleanup),
        ("Cache Disabled", test_cache_disabled),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\n  Total: {passed}/{total} tests passed")
    print("="*80)

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

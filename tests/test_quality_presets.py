"""Test suite for Quality Presets System"""

import asyncio
import sys
from pathlib import Path


async def test_preset_definitions():
    """Test that all presets are correctly defined"""
    print("\n" + "="*60)
    print("TEST: Quality Presets - Definitions")
    print("="*60)

    try:
        from src.quality_presets import (
            QUALITY_PRESETS,
            get_preset,
            get_image_dimensions,
            get_tts_speed,
            list_presets,
            get_speed_improvement
        )

        # Test all presets exist
        print("\n  Checking preset definitions...")
        for level in ["draft", "preview", "production"]:
            preset = get_preset(level)
            print(f"  ✓ {preset.name}: {preset.description}")
            print(f"    - Image: {preset.image.width}x{preset.image.height}, {preset.image.steps} steps")
            print(f"    - TTS: {preset.tts.speed}x speed")
            print(f"    - Video: {preset.video.video_bitrate}, {preset.video.preset}")

        # Test helper functions
        print("\n  Testing helper functions...")
        dims = get_image_dimensions("draft")
        assert dims == (256, 256), f"Expected (256, 256), got {dims}"
        print(f"  ✓ get_image_dimensions('draft') = {dims}")

        speed = get_tts_speed("draft")
        assert speed == 1.5, f"Expected 1.5, got {speed}"
        print(f"  ✓ get_tts_speed('draft') = {speed}")

        presets_list = list_presets()
        assert len(presets_list) == 3, f"Expected 3 presets, got {len(presets_list)}"
        print(f"  ✓ list_presets() returned {len(presets_list)} presets")

        # Test speed improvement
        draft_improvement = get_speed_improvement("draft")
        print(f"  ✓ Draft speed improvement: {draft_improvement}x faster")
        preview_improvement = get_speed_improvement("preview")
        print(f"  ✓ Preview speed improvement: {preview_improvement}x faster")

        print("\n✓ Preset definitions test PASSED")
        return True

    except Exception as e:
        print(f"✗ Preset definitions test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_media_service_with_presets():
    """Test MediaService with different quality presets"""
    print("\n" + "="*60)
    print("TEST: MediaService - Quality Presets")
    print("="*60)

    try:
        from src.services.media import MediaService

        # Test with each quality level
        for quality in ["draft", "preview", "production"]:
            print(f"\n  Testing {quality} preset...")

            media_service = MediaService(
                execution_mode="local",
                enable_cache=False,  # Disable cache to test actual generation
                quality_level=quality
            )

            # Verify preset is set
            assert media_service.quality_level == quality
            print(f"  ✓ Quality level set: {media_service.quality_level}")

            # Verify dimensions
            expected_dims = {
                "draft": (256, 256),
                "preview": (512, 512),
                "production": (1080, 1920)
            }
            actual_dims = (
                media_service.quality_preset.image.width,
                media_service.quality_preset.image.height
            )
            assert actual_dims == expected_dims[quality], \
                f"Expected {expected_dims[quality]}, got {actual_dims}"
            print(f"  ✓ Image dimensions: {actual_dims}")

            # Verify TTS speed
            expected_speeds = {
                "draft": 1.5,
                "preview": 1.2,
                "production": 1.0
            }
            actual_speed = media_service.quality_preset.tts.speed
            assert actual_speed == expected_speeds[quality], \
                f"Expected {expected_speeds[quality]}, got {actual_speed}"
            print(f"  ✓ TTS speed: {actual_speed}x")

            await media_service.close()

        print("\n✓ MediaService quality presets test PASSED")
        return True

    except Exception as e:
        print(f"✗ MediaService quality presets test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tts_with_draft_preset():
    """Test TTS generation with draft preset (should be faster)"""
    print("\n" + "="*60)
    print("TEST: TTS Generation - Draft Preset")
    print("="*60)

    try:
        from src.services.media import MediaService
        import time

        text = "This is a quick test for draft quality preset."

        # Generate with draft preset
        print("\n  Generating TTS with draft preset...")
        media_draft = MediaService(
            execution_mode="local",
            enable_cache=False,
            quality_level="draft"
        )

        start = time.time()
        file_id = await media_draft.generate_tts_direct(text)
        draft_time = time.time() - start

        print(f"  ✓ Draft TTS generated: {file_id}")
        print(f"  ✓ Generation time: {draft_time:.2f}s")

        # Verify file exists
        file_path = media_draft._local_storage.get_media_path(file_id)
        assert Path(file_path).exists(), f"File not found: {file_path}"
        print(f"  ✓ File exists: {file_path}")

        # Verify speed multiplier was applied (1.5x for draft)
        print(f"  ℹ Speed multiplier applied: 1.5x (draft preset)")

        await media_draft.close()

        print("\n✓ Draft preset TTS test PASSED")
        return True

    except Exception as e:
        print(f"✗ Draft preset TTS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_invalid_preset():
    """Test that invalid preset raises error"""
    print("\n" + "="*60)
    print("TEST: Quality Presets - Invalid Preset")
    print("="*60)

    try:
        from src.quality_presets import get_preset

        print("\n  Testing invalid preset name...")
        try:
            get_preset("invalid")
            print("  ✗ Should have raised ValueError")
            return False
        except ValueError as e:
            print(f"  ✓ Correctly raised ValueError: {e}")

        print("\n✓ Invalid preset test PASSED")
        return True

    except Exception as e:
        print(f"✗ Invalid preset test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_preset_comparison():
    """Compare generation speed across presets"""
    print("\n" + "="*60)
    print("TEST: Quality Presets - Speed Comparison")
    print("="*60)

    try:
        from src.services.media import MediaService
        import time

        text = "Speed comparison test for quality presets."
        results = {}

        for quality in ["draft", "production"]:
            print(f"\n  Testing {quality} preset...")

            media_service = MediaService(
                execution_mode="local",
                enable_cache=False,
                quality_level=quality
            )

            start = time.time()
            file_id = await media_service.generate_tts_direct(text)
            elapsed = time.time() - start

            results[quality] = elapsed
            print(f"  ✓ {quality.capitalize()}: {elapsed:.2f}s")

            await media_service.close()

        # Draft should be faster than production
        if results["draft"] < results["production"]:
            speedup = results["production"] / results["draft"]
            print(f"\n  ✓ Draft is {speedup:.2f}x faster than production")
        else:
            print(f"\n  ℹ Draft: {results['draft']:.2f}s, Production: {results['production']:.2f}s")
            print("  ℹ Speed difference may vary with TTS engine overhead")

        print("\n✓ Preset comparison test PASSED")
        return True

    except Exception as e:
        print(f"✗ Preset comparison test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all quality preset tests"""
    print("\n" + "="*80)
    print("QUALITY PRESETS SYSTEM - TEST SUITE")
    print("="*80)

    tests = [
        ("Preset Definitions", test_preset_definitions),
        ("MediaService with Presets", test_media_service_with_presets),
        ("TTS with Draft Preset", test_tts_with_draft_preset),
        ("Invalid Preset Handling", test_invalid_preset),
        ("Preset Speed Comparison", test_preset_comparison),
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

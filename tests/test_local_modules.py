"""Test script for local media modules - Simple verification"""

import sys
from pathlib import Path

def test_config():
    """Test 1: Config module - Device detection"""
    print("\n" + "="*60)
    print("TEST 1: Config Module - Device Detection")
    print("="*60)
    try:
        from src.media_local.config import device, get_device_info, TORCH_AVAILABLE

        print(f"✓ Config imported successfully")
        print(f"  - PyTorch available: {TORCH_AVAILABLE}")
        print(f"  - Device: {device}")

        if TORCH_AVAILABLE:
            info = get_device_info()
            print(f"  - Device info:")
            for key, value in info.items():
                print(f"    • {key}: {value}")

        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_storage():
    """Test 2: Storage Manager - Basic operations"""
    print("\n" + "="*60)
    print("TEST 2: Storage Manager - Basic File Operations")
    print("="*60)
    try:
        from src.media_local.storage.manager import StorageManager, MediaType

        # Create storage in temp directory
        storage_path = Path("./test_storage")
        storage = StorageManager(str(storage_path))

        print(f"✓ StorageManager imported successfully")
        print(f"  - Storage path: {storage_path}")

        # Test upload
        test_data = b"Hello, this is test data!"
        media_id = storage.upload_media(MediaType.AUDIO, test_data, ".txt")
        print(f"✓ File uploaded: {media_id}")

        # Test exists
        exists = storage.media_exists(media_id)
        print(f"✓ File exists check: {exists}")

        # Test retrieve
        retrieved_data = storage.get_media(media_id)
        print(f"✓ File retrieved: {len(retrieved_data)} bytes")
        assert retrieved_data == test_data, "Data mismatch!"

        # Test path
        file_path = storage.get_media_path(media_id)
        print(f"✓ File path: {file_path}")

        # Test delete
        storage.delete_media(media_id)
        print(f"✓ File deleted")

        # Cleanup
        import shutil
        shutil.rmtree(storage_path)
        print(f"✓ Storage cleaned up")

        return True
    except Exception as e:
        print(f"✗ Storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_caption():
    """Test 3: Caption Generator - Subtitle creation"""
    print("\n" + "="*60)
    print("TEST 3: Caption Generator - Subtitle Creation")
    print("="*60)
    try:
        from src.media_local.video.caption import Caption

        caption = Caption()
        print(f"✓ Caption module imported successfully")

        # Test data
        test_captions = [
            {"text": "Hello", "start_ts": 0.0, "end_ts": 0.5},
            {"text": "world", "start_ts": 0.5, "end_ts": 1.0},
            {"text": "!", "start_ts": 1.0, "end_ts": 1.2},
        ]

        # Test English segmentation
        segments = caption.create_subtitle_segments_english(test_captions, max_length=10, lines=1)
        print(f"✓ English segmentation: {len(segments)} segments created")
        for i, seg in enumerate(segments):
            print(f"  [{i+1}] {seg['start_ts']:.2f}s - {seg['end_ts']:.2f}s: {seg['text']}")

        # Test hex to ASS conversion
        ass_color = caption.hex_to_ass("#FF0000", alpha=0.5)
        print(f"✓ Hex to ASS color: #FF0000 -> {ass_color}")

        # Test subtitle file creation
        output_path = Path("./test_subtitle.ass")
        caption.create_subtitle(
            segments,
            dimensions=(1080, 1920),
            output_path=str(output_path),
            font_size=24,
            font_color="#FFFFFF"
        )
        print(f"✓ Subtitle file created: {output_path}")

        # Verify file exists
        if output_path.exists():
            print(f"✓ Subtitle file verified: {output_path.stat().st_size} bytes")
            output_path.unlink()  # Cleanup
            print(f"✓ Subtitle file cleaned up")

        return True
    except Exception as e:
        print(f"✗ Caption test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ffmpeg_wrapper():
    """Test 4: FFmpeg Wrapper - Command availability"""
    print("\n" + "="*60)
    print("TEST 4: FFmpeg Wrapper - Basic Availability")
    print("="*60)
    try:
        from src.media_local.ffmpeg.wrapper import MediaUtils
        import subprocess

        media_utils = MediaUtils()
        print(f"✓ MediaUtils imported successfully")

        # Check if ffmpeg is available
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"✓ FFmpeg available: {version_line}")
            else:
                print(f"⚠ FFmpeg found but returned error")
                return False
        except FileNotFoundError:
            print(f"✗ FFmpeg not found in PATH")
            return False
        except Exception as e:
            print(f"⚠ Error checking FFmpeg: {e}")
            return False

        # Check if ffprobe is available
        try:
            result = subprocess.run(
                ["ffprobe", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"✓ FFprobe available: {version_line}")
            else:
                print(f"⚠ FFprobe found but returned error")
        except FileNotFoundError:
            print(f"⚠ FFprobe not found (needed for some operations)")

        # Test utility methods
        time_formatted = media_utils.format_time(125.5)
        print(f"✓ Time formatting works: 125.5s -> {time_formatted}")

        is_hex = media_utils.is_hex_color("#FF0000")
        print(f"✓ Hex color validation: #FF0000 -> {is_hex}")

        return True
    except Exception as e:
        print(f"✗ FFmpeg wrapper test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  LOCAL MEDIA MODULES - VERIFICATION TESTS".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)

    results = {
        "Config": test_config(),
        "Storage": test_storage(),
        "Caption": test_caption(),
        "FFmpeg Wrapper": test_ffmpeg_wrapper(),
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
        print("\n✓ All basic tests passed! Ready for advanced testing.")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

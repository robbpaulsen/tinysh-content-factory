"""Quick test of local media processing.

Tests:
1. Device detection
2. ChatterboxTTS generation
3. FFmpeg audio info
"""

import asyncio
from pathlib import Path

from loguru import logger

from src.media_local.config import device, get_device_info
from src.media_local.ffmpeg import MediaUtils
from src.media_local.tts import ChatterboxTTS


def test_device_detection():
    """Test 1: Device detection"""
    print("\n" + "=" * 60)
    print("TEST 1: Device Detection")
    print("=" * 60)

    print(f"Device: {device}")
    info = get_device_info()
    for key, value in info.items():
        print(f"  {key}: {value}")

    print("✅ Device detection OK")


def test_chatterbox_tts():
    """Test 2: Chatterbox TTS generation"""
    print("\n" + "=" * 60)
    print("TEST 2: Chatterbox TTS")
    print("=" * 60)

    # Create output directory
    output_dir = Path("./output")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "test_tts.wav"

    # Simple test text
    test_text = "Hello, this is a test of the Chatterbox TTS system. It should generate audio with voice cloning capabilities."

    print(f"Text: {test_text}")
    print(f"Output: {output_path}")

    # Initialize TTS
    tts = ChatterboxTTS()

    # Generate without voice sample (default voice)
    print("\nGenerating audio...")
    success = tts.generate(
        text=test_text,
        output_path=str(output_path),
        temperature=0.8,
        cfg_weight=0.5,
        exaggeration=0.5,
    )

    if success:
        print(f"✅ TTS generation OK: {output_path}")
        return output_path
    else:
        print("❌ TTS generation FAILED")
        return None


def test_ffmpeg_utils(audio_path: Path):
    """Test 3: FFmpeg audio info"""
    print("\n" + "=" * 60)
    print("TEST 3: FFmpeg Utils")
    print("=" * 60)

    if not audio_path or not audio_path.exists():
        print("⚠️  Skipping (no audio file from previous test)")
        return

    utils = MediaUtils()

    print(f"Analyzing: {audio_path}")
    audio_info = utils.get_audio_info(audio_path)

    if audio_info:
        print("\nAudio Info:")
        for key, value in audio_info.items():
            print(f"  {key}: {value}")
        print("✅ FFmpeg utils OK")
    else:
        print("❌ FFmpeg utils FAILED")


def main():
    """Run all tests"""
    print("\n🧪 Testing Local Media Processing")
    print("=" * 60)

    try:
        # Test 1: Device detection
        test_device_detection()

        # Test 2: TTS generation
        audio_path = test_chatterbox_tts()

        # Test 3: FFmpeg utils
        test_ffmpeg_utils(audio_path)

        print("\n" + "=" * 60)
        print("🎉 All tests completed!")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Test failed: {e}")
        print("=" * 60)
        logger.exception("Test error")
        raise


if __name__ == "__main__":
    main()

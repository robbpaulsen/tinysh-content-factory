"""Test TTS modules - Kokoro and Chatterbox"""

import sys
from pathlib import Path
import time


def test_kokoro_tts():
    """Test Kokoro TTS - Simple audio generation"""
    print("\n" + "="*60)
    print("TEST: Kokoro TTS - Audio Generation")
    print("="*60)
    try:
        from src.media_local.tts.kokoro import KokoroTTS

        tts = KokoroTTS()
        print(f"✓ KokoroTTS imported successfully")

        # Test voice listing
        voices = tts.valid_voices("en-us")
        print(f"✓ Available EN-US voices: {len(voices)}")
        print(f"  Sample voices: {voices[:3]}")

        # Test simple generation
        text = "Hello world, this is a test of the Kokoro TTS system."
        output_path = Path("./test_kokoro_output.wav")

        print(f"\n  Generating TTS for: '{text[:50]}...'")
        print(f"  Voice: af_bella")
        print(f"  Please wait, this may take 10-30 seconds on first run...")

        start = time.time()
        captions, duration = tts.generate(
            text=text,
            output_path=str(output_path),
            voice="af_bella",
            speed=1.0
        )
        elapsed = time.time() - start

        print(f"\n✓ Audio generated successfully!")
        print(f"  - Duration: {duration:.2f}s")
        print(f"  - Generation time: {elapsed:.2f}s")
        print(f"  - Speed: {duration/elapsed:.2f}x realtime")
        print(f"  - Captions: {len(captions)} segments")
        print(f"  - Output file: {output_path} ({output_path.stat().st_size} bytes)")

        # Cleanup
        if output_path.exists():
            output_path.unlink()
            print(f"✓ Test file cleaned up")

        return True

    except Exception as e:
        print(f"✗ Kokoro TTS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chatterbox_tts():
    """Test Chatterbox TTS - Voice cloning"""
    print("\n" + "="*60)
    print("TEST: Chatterbox TTS - Voice Cloning")
    print("="*60)
    try:
        from src.media_local.tts.chatterbox import ChatterboxTTS

        tts = ChatterboxTTS()
        print(f"✓ ChatterboxTTS imported successfully")

        # Test simple generation (no voice sample)
        text = "This is a test of the Chatterbox text to speech system."
        output_path = Path("./test_chatterbox_output.wav")

        print(f"\n  Generating TTS for: '{text[:50]}...'")
        print(f"  Mode: Default voice (no cloning)")
        print(f"  Please wait, this may take 30-60 seconds on first run...")

        start = time.time()
        tts.chatterbox(
            text=text,
            output_path=str(output_path),
            sample_audio_path=None,
            exaggeration=0.5,
            cfg_weight=0.5,
            temperature=0.7,
            chunk_chars=1024,
            chunk_silence_ms=350
        )
        elapsed = time.time() - start

        if output_path.exists():
            file_size = output_path.stat().st_size
            print(f"\n✓ Audio generated successfully!")
            print(f"  - Generation time: {elapsed:.2f}s")
            print(f"  - Output file: {output_path} ({file_size} bytes)")

            # Cleanup
            output_path.unlink()
            print(f"✓ Test file cleaned up")
            return True
        else:
            print(f"✗ Output file was not created")
            return False

    except Exception as e:
        print(f"✗ Chatterbox TTS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run TTS tests"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  TTS MODULES - VERIFICATION TESTS".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)

    print("\n⚠ NOTE: First-time model downloads may take several minutes")
    print("         Subsequent runs will be much faster\n")

    results = {}

    # Test Kokoro (faster, smaller model)
    print("\n[1/2] Testing Kokoro TTS...")
    results["Kokoro TTS"] = test_kokoro_tts()

    # Test Chatterbox (slower, larger model)
    if results["Kokoro TTS"]:
        print("\n[2/2] Testing Chatterbox TTS...")
        results["Chatterbox TTS"] = test_chatterbox_tts()
    else:
        print("\n⚠ Skipping Chatterbox test due to Kokoro failure")
        results["Chatterbox TTS"] = False

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
        print("\n✓ All TTS tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} TTS test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

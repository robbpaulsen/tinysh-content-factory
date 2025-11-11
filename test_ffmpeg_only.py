"""Quick test of FFmpeg utils only (no PyTorch needed)."""

from pathlib import Path

from src.media_local.ffmpeg import MediaUtils


def test_ffmpeg_available():
    """Test if ffmpeg/ffprobe are available"""
    print("\n" + "=" * 60)
    print("TEST: FFmpeg Availability")
    print("=" * 60)

    utils = MediaUtils()

    # Try to probe a simple command
    try:
        cmd = ["ffprobe", "-version"]
        success, stdout, stderr = utils.execute_ffprobe_command(cmd, "version check")

        if success and "ffprobe version" in stdout:
            print("✅ FFmpeg/ffprobe available")
            print(f"Version: {stdout.split()[2]}")
            return True
        else:
            print("❌ FFmpeg/ffprobe not found")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run FFmpeg-only test"""
    print("\n🧪 Testing FFmpeg Utils (No PyTorch)")
    print("=" * 60)

    success = test_ffmpeg_available()

    print("\n" + "=" * 60)
    if success:
        print("🎉 FFmpeg utils ready!")
        print("\nYou can use:")
        print("  - MediaUtils.get_audio_info()")
        print("  - MediaUtils.get_video_info()")
        print("  - MediaUtils.merge_videos()")
    else:
        print("❌ FFmpeg not available")
        print("\nInstall FFmpeg: https://ffmpeg.org/download.html")
    print("=" * 60)


if __name__ == "__main__":
    main()

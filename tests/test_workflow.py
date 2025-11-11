"""Test complete workflow using MediaService class with polling."""
import asyncio
import logging
from src.services.media import MediaService

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def main():
    """Test complete video generation workflow."""
    print("=" * 80)
    print("Testing Complete Video Workflow with MediaService")
    print("=" * 80)

    media = MediaService()

    try:
        # Step 1: Generate TTS (with automatic polling)
        print("\n[Step 1] Generating TTS with polling...")
        text = "This is a test of the complete video generation workflow."
        tts_id = await media.generate_tts_direct(text)
        print(f"✅ TTS ready: {tts_id}")

        # Step 2: Generate and upload image
        print("\n[Step 2] Generating image with FLUX...")
        image_url = await media.generate_image_together("A beautiful sunset over mountains")
        print(f"✅ Image generated: {image_url[:80]}...")

        print("  Uploading to media server...")
        image_id = await media.upload_image_from_url(image_url)
        print(f"✅ Image uploaded: {image_id}")

        # Step 3: Generate captioned video (with automatic polling)
        print("\n[Step 3] Generating captioned video with polling...")
        video = await media.generate_captioned_video(image_id, tts_id, text)
        print(f"✅ Video ready: {video.file_id}")

        # Step 4: Merge (even with single video, to test merge endpoint)
        print("\n[Step 4] Merging video (testing merge endpoint)...")
        merged_id = await media.merge_videos([video.file_id])
        print(f"✅ Video merged: {merged_id}")

        # Step 5: Download
        print("\n[Step 5] Getting download URL...")
        download_url = await media.get_download_url(merged_id)
        print(f"✅ Download URL: {download_url}")

        print("\n" + "=" * 80)
        print("✅ COMPLETE WORKFLOW SUCCESS!")
        print("=" * 80)
        print(f"\nFinal video: {merged_id}")
        print(f"Download: {download_url}")

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ WORKFLOW FAILED")
        print("=" * 80)
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await media.close()

if __name__ == "__main__":
    asyncio.run(main())

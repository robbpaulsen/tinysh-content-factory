"""Simple test for video generation endpoints."""
import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def test_video_endpoints():
    """Test video endpoints directly."""
    print("=" * 80)
    print("Testing Video Generation Endpoints")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=120.0) as client:

        # Step 1: Generate TTS first (we know this works now)
        print("\n[Step 1] Generating TTS...")
        tts_response = await client.post(
            f"{BASE_URL}/api/v1/media/audio-tools/tts/chatterbox",
            files={"text": (None, "This is a test video")}
        )
        tts_response.raise_for_status()
        tts_data = tts_response.json()
        tts_id = tts_data["file_id"]
        print(f"✅ TTS generated: {tts_id}")

        # Step 2: Upload a test image (using a public URL)
        print("\n[Step 2] Uploading test image...")
        # Using a simple test image
        test_image_url = "https://picsum.photos/768/1344"

        img_response = await client.post(
            f"{BASE_URL}/api/v1/media/storage",
            data={"url": test_image_url, "media_type": "image"}
        )
        img_response.raise_for_status()
        img_data = img_response.json()
        image_id = img_data["file_id"]
        print(f"✅ Image uploaded: {image_id}")

        # Step 3: Test video generation endpoint
        print("\n[Step 3] Testing video generation endpoint...")
        print(f"  Endpoint: {BASE_URL}/api/v1/media/video-tools/generate/tts-captioned-video")
        print(f"  Payload: background_id={image_id}, audio_id={tts_id}")

        try:
            # Use files= for multipart/form-data (like curl -F)
            video_files = {
                "background_id": (None, image_id),
                "audio_id": (None, tts_id),
                "text": (None, "This is a test video"),
                "width": (None, "768"),
                "height": (None, "1344"),
            }

            video_response = await client.post(
                f"{BASE_URL}/api/v1/media/video-tools/generate/tts-captioned-video",
                files=video_files,
                timeout=300.0  # 5 minutes
            )
            video_response.raise_for_status()
            video_data = video_response.json()

            print(f"✅ Response: {video_data}")
            video_id = video_data["file_id"]
            print(f"  → Video generated: {video_id}")

        except httpx.HTTPStatusError as e:
            print(f"  ❌ HTTP Error {e.response.status_code}")
            print(f"     Response: {e.response.text}")
            return
        except Exception as e:
            print(f"  ❌ Error: {type(e).__name__}: {e}")
            return

        # Step 4: Test video merge endpoint
        print("\n[Step 4] Testing video merge endpoint...")
        print(f"  Endpoint: {BASE_URL}/api/v1/media/video-tools/merge")

        try:
            # Use files= for multipart/form-data (like curl -F)
            # video_ids must be comma-separated string
            merge_files = {
                "video_ids": (None, video_id)  # Just one video for testing
            }

            merge_response = await client.post(
                f"{BASE_URL}/api/v1/media/video-tools/merge",
                files=merge_files,
                timeout=600.0  # 10 minutes
            )
            merge_response.raise_for_status()
            merge_data = merge_response.json()

            print(f"✅ Response: {merge_data}")
            final_video_id = merge_data["file_id"]
            print(f"  → Video merged: {final_video_id}")

            print(f"\n✅ Final video ID: {final_video_id}")
            print(f"   Download URL: {BASE_URL}/api/v1/media/storage/{final_video_id}/download")

        except httpx.HTTPStatusError as e:
            print(f"  ❌ HTTP Error {e.response.status_code}")
            print(f"     Response: {e.response.text}")
            return
        except Exception as e:
            print(f"  ❌ Error: {type(e).__name__}: {e}")
            return

    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_video_endpoints())

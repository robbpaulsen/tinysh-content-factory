"""Media service for interacting with local media processing server."""

import asyncio
import logging
import time
from pathlib import Path

import httpx
from aiolimiter import AsyncLimiter
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models import GeneratedImage, GeneratedTTS, GeneratedVideo, MediaProcessingStatus

logger = logging.getLogger(__name__)


class MediaService:
    """Service for media processing via local server."""

    def __init__(self, base_url: str | None = None):
        """
        Initialize media service.

        Args:
            base_url: Base URL of media server (defaults to settings.media_server_url)
        """
        self.base_url = (base_url or settings.media_server_url).rstrip("/")
        self.client = httpx.AsyncClient(timeout=settings.http_timeout)
        # Rate limiter for Together.ai FLUX: 6 images per minute
        self.flux_limiter = AsyncLimiter(6, 60)
        logger.info(f"Initialized media service: {self.base_url}")

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def wait_for_file_ready(self, file_id: str, poll_interval: float = 0.5, timeout: float = 60.0) -> bool:
        """
        Wait for a file to be ready after background processing.

        Args:
            file_id: File ID to wait for
            poll_interval: Seconds between status checks
            timeout: Maximum wait time

        Returns:
            True if file is ready, False if timeout or not found
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = await self.client.get(f"{self.base_url}/api/v1/media/storage/{file_id}/status")
                response.raise_for_status()
                status_data = response.json()

                if status_data.get("status") == "ready":
                    logger.debug(f"File {file_id} is ready")
                    return True
                elif status_data.get("status") == "not_found":
                    logger.warning(f"File {file_id} not found")
                    return False
                # If "processing", continue waiting

            except Exception as e:
                logger.warning(f"Error checking file status: {e}")

            await asyncio.sleep(poll_interval)

        logger.warning(f"Timeout waiting for file {file_id} to be ready")
        return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def health_check(self) -> bool:
        """
        Check if media server is healthy.

        Returns:
            True if server is responsive
        """
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            logger.info("Media server health check passed")
            return True
        except Exception as e:
            logger.error(f"Media server health check failed: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def generate_image_together(self, prompt: str) -> str:
        """
        Generate image using Together.ai FLUX API with rate limiting.

        Args:
            prompt: Image generation prompt

        Returns:
            Image URL from Together.ai
        """
        logger.info(f"Generating image with Together.ai: {prompt[:100]}...")

        url = "https://api.together.xyz/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {settings.together_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.flux_model,
            "prompt": prompt,
            "width": settings.image_width,
            "height": settings.image_height,
            "steps": 4,  # FLUX Schnell uses 4 steps
        }

        # Apply rate limiting: 6 images per minute
        async with self.flux_limiter:
            response = await self.client.post(url, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()

            data = response.json()
            image_url = data["data"][0]["url"]

            logger.info(f"Image generated successfully: {image_url}")
            return image_url

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def upload_image_from_url(self, image_url: str) -> str:
        """
        Upload image from URL to media server.

        Args:
            image_url: URL of image to upload

        Returns:
            File ID from media server
        """
        logger.info(f"Uploading image to media server: {image_url}")

        data = {
            "url": image_url,
            "media_type": "image"
        }

        response = await self.client.post(
            f"{self.base_url}/api/v1/media/storage",
            data=data,  # multipart/form-data format
        )
        response.raise_for_status()

        response_data = response.json()
        file_id = response_data["file_id"]

        logger.info(f"Image uploaded with file_id: {file_id}")
        return file_id

    async def generate_and_upload_image(self, prompt: str) -> GeneratedImage:
        """
        Generate image with Together.ai and upload to media server.

        Args:
            prompt: Image generation prompt

        Returns:
            GeneratedImage with URL and file_id
        """
        image_url = await self.generate_image_together(prompt)
        file_id = await self.upload_image_from_url(image_url)

        return GeneratedImage(url=image_url, file_id=file_id)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def generate_tts_direct(self, text: str) -> str:
        """
        Generate TTS on media server (Kokoro or Chatterbox).
        Returns file_id directly (synchronous response).

        Args:
            text: Text to convert to speech

        Returns:
            File ID of generated audio
        """
        logger.info(f"Generating TTS: {text[:100]}...")

        if settings.tts_engine == "kokoro":
            endpoint = f"{self.base_url}/api/v1/media/audio-tools/tts/kokoro"
            # Use files= parameter to send multipart/form-data (like curl -F)
            files = {
                "text": (None, text),
                "voice": (None, settings.kokoro_voice),
                "speed": (None, str(settings.kokoro_speed)),
            }
        else:  # chatterbox
            endpoint = f"{self.base_url}/api/v1/media/audio-tools/tts/chatterbox"
            # Use files= parameter to send multipart/form-data (like curl -F)
            files = {
                "text": (None, text),
                "exaggeration": (None, str(settings.chatterbox_exaggeration)),
                "cfg_weight": (None, str(settings.chatterbox_cfg_weight)),
                "temperature": (None, str(settings.chatterbox_temperature)),
            }
            # Handle voice sample - check if it's a local path or file_id
            if settings.chatterbox_voice_sample_id:
                voice_sample = settings.chatterbox_voice_sample_id
                # If it's a local file path, upload it first
                if voice_sample.startswith(("D:", "C:", "/", ".", "\\")):
                    logger.warning(
                        f"CHATTERBOX_VOICE_SAMPLE_ID appears to be a local path: {voice_sample}. "
                        "Upload this file to the media server first and use the file_id instead."
                    )
                    # For now, skip it to avoid 404 error
                else:
                    files["sample_audio_id"] = (None, voice_sample)

        response = await self.client.post(endpoint, files=files, timeout=120.0)
        response.raise_for_status()

        data = response.json()
        file_id = data["file_id"]

        logger.info(f"TTS generation started with file_id: {file_id}, waiting for completion...")

        # Wait for background task to complete
        # TTS is the slowest operation, poll every 15 seconds
        ready = await self.wait_for_file_ready(file_id, poll_interval=15.0, timeout=120.0)
        if not ready:
            raise RuntimeError(f"TTS file {file_id} did not become ready in time")

        logger.info(f"TTS generated and ready: {file_id}")
        return file_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_processing_status(self, task_id: str) -> MediaProcessingStatus:
        """
        Get status of a processing task.

        Args:
            task_id: Task ID to check

        Returns:
            MediaProcessingStatus
        """
        response = await self.client.get(f"{self.base_url}/api/v1/tasks/{task_id}/status")
        response.raise_for_status()

        data = response.json()
        return MediaProcessingStatus(**data)

    async def wait_for_processing(
        self, task_id: str, poll_interval: float = 2.0, timeout: float | None = None
    ) -> MediaProcessingStatus:
        """
        Poll task status until completion or timeout.

        Args:
            task_id: Task ID to monitor
            poll_interval: Seconds between status checks
            timeout: Maximum wait time (defaults to settings.media_processing_timeout)

        Returns:
            Final MediaProcessingStatus

        Raises:
            TimeoutError: If processing exceeds timeout
            RuntimeError: If processing fails
        """
        timeout = timeout or settings.media_processing_timeout
        start_time = time.time()

        logger.info(f"Waiting for task {task_id} to complete...")

        while True:
            status = await self.get_processing_status(task_id)

            if status.status == "ready":
                logger.info(f"Task {task_id} completed successfully")
                return status
            elif status.status == "failed":
                error_msg = status.error or "Unknown error"
                logger.error(f"Task {task_id} failed: {error_msg}")
                raise RuntimeError(f"Processing failed: {error_msg}")
            elif status.status == "not_found":
                logger.error(f"Task {task_id} not found")
                raise RuntimeError(f"Task not found: {task_id}")

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.error(f"Task {task_id} timed out after {elapsed:.1f}s")
                raise TimeoutError(f"Processing timeout after {timeout}s")

            # Still processing, wait and retry
            await asyncio.sleep(poll_interval)

    async def generate_tts(self, text: str) -> GeneratedTTS:
        """
        Generate TTS audio (returns immediately with file_id).

        Args:
            text: Text to convert to speech

        Returns:
            GeneratedTTS with file_id
        """
        file_id = await self.generate_tts_direct(text)
        return GeneratedTTS(file_id=file_id, duration=None)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def start_captioned_video_generation(
        self, image_id: str, tts_id: str, text: str
    ) -> str:
        """
        Start generating video with captions.

        Args:
            image_id: Background image file_id
            tts_id: TTS audio file_id
            text: Text for captions

        Returns:
            file_id (synchronous response)
        """
        logger.info(f"Starting captioned video generation: image={image_id}, tts={tts_id}")

        # Use files= for multipart/form-data (like curl -F)
        files = {
            "background_id": (None, image_id),
            "audio_id": (None, tts_id),
            "text": (None, text),
            "width": (None, str(settings.image_width)),
            "height": (None, str(settings.image_height)),
        }

        response = await self.client.post(
            f"{self.base_url}/api/v1/media/video-tools/generate/tts-captioned-video",
            files=files,
            timeout=300.0  # 5 minutes for video generation
        )
        response.raise_for_status()

        data = response.json()
        file_id = data["file_id"]

        logger.info(f"Video generation started with file_id: {file_id}, waiting for completion...")

        # Wait for background task to complete (video generation can take time)
        # Poll every 10 seconds (second/third pause in n8n workflow)
        ready = await self.wait_for_file_ready(file_id, poll_interval=10.0, timeout=300.0)
        if not ready:
            raise RuntimeError(f"Video file {file_id} did not become ready in time")

        logger.info(f"Video generated and ready: {file_id}")
        return file_id

    async def generate_captioned_video(
        self, image_id: str, tts_id: str, text: str
    ) -> GeneratedVideo:
        """
        Generate video with captions (synchronous operation).

        Args:
            image_id: Background image file_id
            tts_id: TTS audio file_id
            text: Text for captions

        Returns:
            GeneratedVideo with file_id
        """
        file_id = await self.start_captioned_video_generation(image_id, tts_id, text)
        return GeneratedVideo(file_id=file_id, tts_id=tts_id, image_id=image_id)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def start_video_merge(
        self, video_ids: list[str], background_music_id: str | None = None
    ) -> str:
        """
        Start merging multiple videos with optional background music.

        Args:
            video_ids: List of video file_ids to merge
            background_music_id: Optional background music file_id

        Returns:
            file_id (synchronous response)
        """
        logger.info(f"Starting video merge: {len(video_ids)} videos")

        # Convert list to comma-separated string and use files= for multipart/form-data
        files = {"video_ids": (None, ",".join(video_ids))}

        if background_music_id:
            files["background_music_id"] = (None, background_music_id)
            files["background_music_volume"] = (None, str(settings.background_music_volume))

        # Use files= for multipart/form-data (like curl -F)
        response = await self.client.post(
            f"{self.base_url}/api/v1/media/video-tools/merge",
            files=files,
            timeout=600.0  # 10 minutes for merging
        )
        response.raise_for_status()

        data = response.json()
        file_id = data["file_id"]

        logger.info(f"Video merge started with file_id: {file_id}, waiting for completion...")

        # Wait for background task to complete (merge can take time with music)
        # Poll every 5 seconds (fourth/last pause in n8n workflow)
        ready = await self.wait_for_file_ready(file_id, poll_interval=5.0, timeout=600.0)
        if not ready:
            raise RuntimeError(f"Merged video file {file_id} did not become ready in time")

        logger.info(f"Video merged and ready: {file_id}")
        return file_id

    async def upload_local_file_if_needed(self, file_path_or_id: str, media_type: str) -> str:
        """
        Upload a local file to the server if it's a path, otherwise return the ID.

        Args:
            file_path_or_id: Either a local file path or a server file_id
            media_type: Type of media (audio, image, video)

        Returns:
            Server file_id
        """
        # Check if it's a local path
        if file_path_or_id.startswith(("D:", "C:", "/", ".", "\\")):
            logger.info(f"Uploading local file to server: {file_path_or_id}")
            local_path = Path(file_path_or_id)

            if not local_path.exists():
                raise FileNotFoundError(f"Local file not found: {file_path_or_id}")

            # Read file and upload
            file_data = local_path.read_bytes()
            file_extension = local_path.suffix

            # Upload using multipart/form-data
            files = {
                "file": (local_path.name, file_data),
                "media_type": (None, media_type)
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/media/storage",
                files=files
            )
            response.raise_for_status()
            data = response.json()
            file_id = data["file_id"]

            logger.info(f"Local file uploaded with file_id: {file_id}")
            return file_id
        else:
            # Already a file_id
            return file_path_or_id

    async def merge_videos(
        self, video_ids: list[str], background_music_id: str | None = None
    ) -> str:
        """
        Merge videos (synchronous operation).

        Args:
            video_ids: List of video file_ids to merge
            background_music_id: Optional background music file_id or local path

        Returns:
            Final merged video file_id
        """
        # Upload background music if it's a local path
        if background_music_id:
            background_music_id = await self.upload_local_file_if_needed(
                background_music_id, "audio"
            )

        file_id = await self.start_video_merge(video_ids, background_music_id)
        return file_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_download_url(self, file_id: str) -> str:
        """
        Get download URL for a file.

        Args:
            file_id: File ID from media server

        Returns:
            Download URL
        """
        return f"{self.base_url}/api/v1/media/storage/{file_id}/download"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def download_file(self, file_id: str, output_path: Path):
        """
        Download file from media server.

        Args:
            file_id: File ID to download
            output_path: Local path to save file
        """
        logger.info(f"Downloading file {file_id} to {output_path}")

        url = await self.get_download_url(file_id)
        response = await self.client.get(url)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        logger.info(f"File downloaded successfully: {output_path}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def delete_file(self, file_id: str):
        """
        Delete a file from media server.

        Args:
            file_id: File ID to delete
        """
        logger.info(f"Deleting file: {file_id}")

        response = await self.client.delete(f"{self.base_url}/api/v1/media/storage/{file_id}")
        response.raise_for_status()

        logger.info(f"File deleted: {file_id}")

    async def cleanup_files(self, file_ids: list[str]):
        """
        Delete multiple files from media server.

        Args:
            file_ids: List of file IDs to delete
        """
        logger.info(f"Cleaning up {len(file_ids)} files")

        for file_id in file_ids:
            try:
                await self.delete_file(file_id)
            except Exception as e:
                logger.warning(f"Failed to delete file {file_id}: {e}")

        logger.info("Cleanup completed")

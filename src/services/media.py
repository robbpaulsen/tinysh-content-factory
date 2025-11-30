"""Media service for interacting with local media processing server."""

import asyncio
import logging
import time
from pathlib import Path

import httpx
from aiolimiter import AsyncLimiter
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.constants import TIMEOUT_TTS_GENERATION
from src.models import GeneratedImage, GeneratedTTS, GeneratedVideo, MediaProcessingStatus
from src.services.cache import AssetCache

logger = logging.getLogger(__name__)


class MediaService:
    """Service for media processing via local server or local modules.

    Supports two execution modes:
    - 'remote': Uses HTTP API to communicate with Docker server (default)
    - 'local': Uses local media_local modules directly (faster, no HTTP overhead)
    """

    def __init__(self, base_url: str | None = None, execution_mode: str = "remote", enable_cache: bool = True):
        """
        Initialize media service.

        Args:
            base_url: Base URL of media server (defaults to settings.media_server_url)
            execution_mode: 'remote' (HTTP API) or 'local' (direct modules)
            enable_cache: Whether to enable smart caching (default: True)
        """
        self.execution_mode = execution_mode
        self.base_url = (base_url or settings.media_server_url).rstrip("/")
        self.client = httpx.AsyncClient(timeout=settings.http_timeout)
        # Rate limiter for Together.ai FLUX: 6 images per minute
        self.flux_limiter = AsyncLimiter(6, 60)

        # Local execution components (lazy loaded)
        self._local_storage = None
        self._local_media_utils = None
        self._local_kokoro_tts = None
        self._local_chatterbox_tts = None
        self._local_caption = None
        self._local_video_builder = None

        # Smart cache for assets
        self.enable_cache = enable_cache
        if enable_cache:
            cache_dir = Path("./media_local_storage/cache")
            self.cache = AssetCache(
                cache_dir=cache_dir,
                similarity_threshold=0.85,
                enable_similarity=True
            )
            logger.info("Smart cache enabled")
        else:
            self.cache = None
            logger.info("Smart cache disabled")

        if execution_mode == "local":
            logger.info(f"Initialized media service in LOCAL mode")
            self._init_local_modules()
        else:
            logger.info(f"Initialized media service in REMOTE mode: {self.base_url}")

    def _init_local_modules(self):
        """Initialize local media processing modules."""
        from src.media_local.storage.manager import StorageManager, MediaType
        from src.media_local.ffmpeg.wrapper import MediaUtils
        from src.media_local.tts.kokoro import KokoroTTS
        from src.media_local.tts.chatterbox import ChatterboxTTS
        from src.media_local.video.caption import Caption
        from src.media_local.video.builder import VideoBuilder

        # Initialize storage
        storage_path = Path("./media_local_storage")
        self._local_storage = StorageManager(str(storage_path))

        # Initialize media utils
        self._local_media_utils = MediaUtils()

        # Initialize TTS engines (lazy - only when needed)
        # self._local_kokoro_tts = KokoroTTS()
        # self._local_chatterbox_tts = ChatterboxTTS()

        # Initialize caption generator
        self._local_caption = Caption()

        logger.info("Local media modules initialized")

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (or empty dict if cache disabled)
        """
        if not self.cache:
            return {"enabled": False}

        stats = self.cache.get_stats()
        stats["enabled"] = True
        return stats

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
    async def generate_image_together(self, prompt: str, negative_prompt: str | None = None) -> str:
        """
        Generate image using Together.ai FLUX API with rate limiting.

        Args:
            prompt: Image generation prompt
            negative_prompt: Negative prompt (passed as separate parameter)

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
        
        # Add negative_prompt parameter if provided
        # Confirmed: Together API supports negative_prompt for FLUX models
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
            logger.info("Applied negative_prompt to request payload")

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

    async def generate_and_upload_image(self, prompt: str, negative_prompt: str | None = None) -> GeneratedImage:
        """
        Generate image with Together.ai and upload to media server.

        Args:
            prompt: Image generation prompt
            negative_prompt: Negative prompt (converted to positive guidance for FLUX)

        Returns:
            GeneratedImage with URL and file_id
        """
        # Check cache first
        cache_key = f"{prompt}|{negative_prompt or ''}"
        if self.cache:
            cached = self.cache.get("image", cache_key)
            if cached:
                file_path, metadata = cached
                logger.info(f"Cache HIT for image: {metadata['match_type']} match")
                # For local mode, file_path is the file_id
                if self.execution_mode == "local":
                    # Extract file_id from path
                    file_id = Path(file_path).stem.split("_")[0] if "_" in Path(file_path).stem else Path(file_path).stem
                    return GeneratedImage(url=file_path, file_id=file_id)
                else:
                    # For remote mode, need to upload cached file
                    file_id = await self.upload_local_file_if_needed(file_path, "image")
                    return GeneratedImage(url=file_path, file_id=file_id)

        # Cache miss - generate new image
        logger.info("Cache MISS for image - generating...")
        image_url = await self.generate_image_together(prompt, negative_prompt=negative_prompt)
        file_id = await self.upload_image_from_url(image_url)

        # Store in cache
        if self.cache and self.execution_mode == "local":
            # For local mode, cache the downloaded file
            file_path = self._local_storage.get_media_path(file_id)
            self.cache.put("image", cache_key, file_path, {"prompt": prompt, "negative_prompt": negative_prompt})

        return GeneratedImage(url=image_url, file_id=file_id)

    def _generate_tts_local(self, text: str, voice_config: dict | None = None) -> str:
        """Generate TTS locally using media_local modules.

        Args:
            text: Text to convert to speech
            voice_config: Optional voice configuration

        Returns:
            File ID of generated audio
        """
        # Determine engine and build cache key
        if voice_config:
            engine = voice_config.get("engine", "kokoro")
        else:
            engine = getattr(settings, "tts_engine", "kokoro")

        # Build cache key from text + voice config
        import json
        config_str = json.dumps(voice_config, sort_keys=True) if voice_config else ""
        cache_key = f"{text}|{engine}|{config_str}"

        # Check cache first
        if self.cache:
            cached = self.cache.get("tts", cache_key)
            if cached:
                file_path, metadata = cached
                logger.info(f"Cache HIT for TTS: {metadata['match_type']} match")
                # Copy cached file to storage with new file_id
                import shutil
                file_id, new_file_path = self._local_storage.create_media_filename_with_id("audio", ".wav")
                shutil.copy2(file_path, new_file_path)
                logger.info(f"Copied cached file to: {file_id}")
                return file_id

        # Cache miss - generate new TTS
        logger.info(f"Cache MISS for TTS - generating locally: {text[:100]}...")

        # Create output file
        file_id, file_path = self._local_storage.create_media_filename_with_id("audio", ".wav")

        if engine == "kokoro":
            # Lazy load Kokoro TTS
            if not self._local_kokoro_tts:
                from src.media_local.tts.kokoro import KokoroTTS
                self._local_kokoro_tts = KokoroTTS()

            voice = voice_config.get("voice", "af_bella") if voice_config else getattr(settings, "kokoro_voice", "af_bella")
            speed = voice_config.get("speed", 1.0) if voice_config else getattr(settings, "kokoro_speed", 1.0)

            # Generate audio
            self._local_kokoro_tts.generate(text, file_path, voice=voice, speed=speed)

        else:  # chatterbox
            # Lazy load Chatterbox TTS
            if not self._local_chatterbox_tts:
                from src.media_local.tts.chatterbox import ChatterboxTTS
                self._local_chatterbox_tts = ChatterboxTTS()

            exaggeration = voice_config.get("exaggeration", 0.5) if voice_config else getattr(settings, "chatterbox_exaggeration", 0.5)
            cfg_weight = voice_config.get("cfg_weight", 0.5) if voice_config else getattr(settings, "chatterbox_cfg_weight", 0.5)
            temperature = voice_config.get("temperature", 0.7) if voice_config else getattr(settings, "chatterbox_temperature", 0.7)
            sample_path = voice_config.get("sample_path") if voice_config else getattr(settings, "chatterbox_voice_sample_id", None)

            # Generate audio
            self._local_chatterbox_tts.generate(
                text=text,
                output_path=file_path,
                sample_audio_path=sample_path,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
                temperature=temperature
            )

        logger.info(f"TTS generated locally: {file_id}")

        # Store in cache
        if self.cache:
            self.cache.put("tts", cache_key, file_path, {"text": text, "engine": engine, "voice_config": voice_config})

        return file_id

    def _generate_captioned_video_local(
        self, image_id: str, tts_id: str, text: str, subtitle_config: dict | None = None
    ) -> str:
        """Generate captioned video locally using media_local modules.

        Args:
            image_id: Background image file_id
            tts_id: TTS audio file_id
            text: Text for captions
            subtitle_config: Optional subtitle styling configuration

        Returns:
            File ID of generated video
        """
        logger.info(f"Generating captioned video locally: image={image_id}, tts={tts_id}")

        # Lazy load video builder if needed
        if not self._local_video_builder:
            from src.media_local.video.builder import VideoBuilder

            # Create builder with dimensions from settings
            dimensions = (settings.image_width, settings.image_height)
            self._local_video_builder = VideoBuilder(dimensions=dimensions)
            self._local_video_builder.set_media_utils(self._local_media_utils)

        # Get file paths from storage
        image_path = self._local_storage.get_media_path(image_id)
        audio_path = self._local_storage.get_media_path(tts_id)

        # Create output video file
        video_file_id, video_path = self._local_storage.create_media_filename_with_id("video", ".mp4")

        # Generate subtitle file
        subtitle_file_id, subtitle_path = self._local_storage.create_media_filename_with_id("video", ".ass")

        # Parse subtitle config
        config = subtitle_config or {}
        font_size = config.get("font_size", 24)
        font_color = config.get("color", "#FFFFFF")
        font_name = config.get("font", "Arial")
        font_bold = config.get("bold", True)
        stroke_color = config.get("outline_color", "#000000")
        stroke_size = config.get("outline_width", 3)
        shadow_blur = config.get("shadow", 0)
        max_lines = config.get("max_lines", 2)
        max_length = config.get("max_length", 80)

        # Map alignment (2=bottom, 5=top, 10=center)
        align_num = config.get("alignment", 2)
        position_map = {2: "bottom", 5: "top", 10: "center"}
        subtitle_position = position_map.get(align_num, "bottom")

        # Generate subtitle segments from text
        # For simplicity, create basic captions - in a real scenario you'd use TTS-generated captions
        # Create simple segments based on text
        words = text.split()
        segments = []
        current_time = 0.0
        words_per_segment = max_length // 10  # Rough estimate

        for i in range(0, len(words), words_per_segment):
            segment_words = words[i:i+words_per_segment]
            segment_text = " ".join(segment_words)
            duration = len(segment_text) * 0.05  # Rough estimate: 50ms per character

            segments.append({
                "text": segment_text,
                "start_ts": current_time,
                "end_ts": current_time + duration
            })
            current_time += duration

        # Create subtitle file using Caption
        dimensions = (settings.image_width, settings.image_height)
        self._local_caption.create_subtitle(
            segments=segments,
            dimensions=dimensions,
            output_path=subtitle_path,
            font_size=font_size,
            font_color=font_color,
            font_name=font_name,
            font_bold=font_bold,
            stroke_color=stroke_color,
            stroke_size=stroke_size,
            shadow_blur=shadow_blur,
            subtitle_position=subtitle_position
        )

        # Build video using VideoBuilder
        self._local_video_builder.set_background_image(image_path)
        self._local_video_builder.set_audio(audio_path)
        self._local_video_builder.set_captions(subtitle_path, config={"style": {}})
        self._local_video_builder.set_output_path(video_path)

        # Execute video build
        success = self._local_video_builder.execute()

        if not success:
            raise RuntimeError("Failed to generate video locally")

        logger.info(f"Captioned video generated locally: {video_file_id}")
        return video_file_id

    def _merge_videos_local(
        self,
        video_ids: list[str],
        background_music_id: str | None = None,
        music_volume: float | None = None
    ) -> str:
        """Merge videos locally using media_local modules.

        Args:
            video_ids: List of video file_ids to merge
            background_music_id: Optional background music file_id
            music_volume: Optional music volume (0.0-1.0)

        Returns:
            File ID of merged video
        """
        logger.info(f"Merging {len(video_ids)} videos locally")

        # Get video paths from storage
        video_paths = [self._local_storage.get_media_path(vid) for vid in video_ids]

        # Create output video file
        output_file_id, output_path = self._local_storage.create_media_filename_with_id("video", ".mp4")

        # Build concat file for FFmpeg
        concat_file_id, concat_path = self._local_storage.create_media_filename_with_id("video", ".txt")
        with open(concat_path, "w") as f:
            for video_path in video_paths:
                # FFmpeg concat format requires absolute paths on Windows with forward slashes
                # Convert to absolute path first, then replace backslashes
                abs_path = str(Path(video_path).absolute()).replace("\\", "/")
                f.write(f"file '{abs_path}'\n")

        # Build FFmpeg command
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_path]

        # Add background music if provided
        if background_music_id:
            music_path = self._local_storage.get_media_path(background_music_id)
            volume = music_volume if music_volume is not None else 0.1

            cmd.extend(["-i", music_path])
            # Mix audio: video audio + background music
            cmd.extend([
                "-filter_complex",
                f"[0:a]volume=1.0[a1];[1:a]volume={volume}[a2];[a1][a2]amix=inputs=2:duration=first[aout]",
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23",
                "-c:a", "aac", "-b:a", "128k"
            ])
        else:
            # No music - just copy streams (much faster)
            cmd.extend(["-c", "copy"])

        cmd.append(output_path)

        # Execute FFmpeg command
        success = self._local_media_utils.execute_ffmpeg_command(
            cmd,
            "merge videos",
            show_progress=True
        )

        if not success:
            raise RuntimeError("Failed to merge videos locally")

        logger.info(f"Videos merged locally: {output_file_id}")
        return output_file_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def generate_tts_direct(self, text: str, voice_config: dict | None = None) -> str:
        """
        Generate TTS on media server (Kokoro or Chatterbox).
        Returns file_id directly (synchronous response).

        Args:
            text: Text to convert to speech
            voice_config: Optional voice configuration from ProfileManager
                         (if None, uses settings for backward compatibility)

        Returns:
            File ID of generated audio
        """
        # Use local execution if enabled
        if self.execution_mode == "local":
            return self._generate_tts_local(text, voice_config)

        logger.info(f"Generating TTS: {text[:100]}...")

        # Use voice_config if provided, otherwise fall back to settings
        if voice_config:
            engine = voice_config.get("engine", "kokoro")
        else:
            engine = getattr(settings, "tts_engine", "kokoro")

        if engine == "kokoro":
            endpoint = f"{self.base_url}/api/v1/media/audio-tools/tts/kokoro"
            # Use files= parameter to send multipart/form-data (like curl -F)
            if voice_config:
                voice = voice_config.get("voice", "af_bella")
                speed = voice_config.get("speed", 1.0)
            else:
                voice = getattr(settings, "kokoro_voice", "af_bella")
                speed = getattr(settings, "kokoro_speed", 1.0)

            files = {
                "text": (None, text),
                "voice": (None, voice),
                "speed": (None, str(speed)),
            }
        else:  # chatterbox
            endpoint = f"{self.base_url}/api/v1/media/audio-tools/tts/chatterbox"
            # Use files= parameter to send multipart/form-data (like curl -F)
            if voice_config:
                exaggeration = voice_config.get("exaggeration", 0.5)
                cfg_weight = voice_config.get("cfg_weight", 0.5)
                temperature = voice_config.get("temperature", 0.7)
                sample_path = voice_config.get("sample_path")
            else:
                exaggeration = getattr(settings, "chatterbox_exaggeration", 0.5)
                cfg_weight = getattr(settings, "chatterbox_cfg_weight", 0.5)
                temperature = getattr(settings, "chatterbox_temperature", 0.7)
                sample_path = getattr(settings, "chatterbox_voice_sample_id", None)

            files = {
                "text": (None, text),
                "exaggeration": (None, str(exaggeration)),
                "cfg_weight": (None, str(cfg_weight)),
                "temperature": (None, str(temperature)),
            }
            # Handle voice sample - check if it's a local path or file_id
            if sample_path:
                voice_sample = sample_path
                # If it's a local file path, upload it first
                if voice_sample.startswith(("D:", "C:", "/", ".", "\\")):
                    logger.info(f"Uploading local voice sample to media server: {voice_sample}")
                    # Upload the file and get file_id
                    voice_sample_file_id = await self.upload_local_file_if_needed(voice_sample, "audio")
                    files["sample_audio_id"] = (None, voice_sample_file_id)
                    logger.info(f"Voice sample uploaded with file_id: {voice_sample_file_id}")
                else:
                    files["sample_audio_id"] = (None, voice_sample)

        response = await self.client.post(endpoint, files=files, timeout=TIMEOUT_TTS_GENERATION)
        response.raise_for_status()

        data = response.json()
        file_id = data["file_id"]

        logger.info(f"TTS generation started with file_id: {file_id}, waiting for completion...")

        # Wait for background task to complete
        # TTS is the slowest operation, poll every 15 seconds
        ready = await self.wait_for_file_ready(file_id, poll_interval=15.0, timeout=TIMEOUT_TTS_GENERATION)
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

    async def generate_tts(self, text: str, voice_config: dict | None = None) -> GeneratedTTS:
        """
        Generate TTS audio (returns immediately with file_id).

        Args:
            text: Text to convert to speech
            voice_config: Optional voice configuration from ProfileManager

        Returns:
            GeneratedTTS with file_id
        """
        file_id = await self.generate_tts_direct(text, voice_config)
        return GeneratedTTS(file_id=file_id, duration=None)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def start_captioned_video_generation(
        self, image_id: str, tts_id: str, text: str, subtitle_config: dict | None = None
    ) -> str:
        """
        Start generating video with captions.

        Args:
            image_id: Background image file_id
            tts_id: TTS audio file_id
            text: Text for captions
            subtitle_config: Optional subtitle styling configuration

        Returns:
            file_id (synchronous response)
        """
        # Use local execution if enabled
        if self.execution_mode == "local":
            return self._generate_captioned_video_local(image_id, tts_id, text, subtitle_config)

        logger.info(f"Starting captioned video generation: image={image_id}, tts={tts_id}")

        # Use files= for multipart/form-data (like curl -F)
        files = {
            "background_id": (None, image_id),
            "audio_id": (None, tts_id),
            "text": (None, text),
            "width": (None, str(settings.image_width)),
            "height": (None, str(settings.image_height)),
        }
        
        # Map subtitle config to server parameters
        if subtitle_config:
            if subtitle_config.get("font"):
                files["caption_config_font_name"] = (None, subtitle_config["font"])
            
            if subtitle_config.get("font_size"):
                files["caption_config_font_size"] = (None, str(subtitle_config["font_size"]))
                
            if subtitle_config.get("bold") is not None:
                # Convert bool to string "true"/"false" for form data, or let requests handle it if it accepts bools. 
                # Safest is string.
                files["caption_config_font_bold"] = (None, str(subtitle_config["bold"]).lower())
                
            if subtitle_config.get("color"):
                files["caption_config_font_color"] = (None, subtitle_config["color"])
                
            if subtitle_config.get("outline_color"):
                files["caption_config_stroke_color"] = (None, subtitle_config["outline_color"])
                
            if subtitle_config.get("outline_width"):
                files["caption_config_stroke_size"] = (None, str(subtitle_config["outline_width"]))
                
            if subtitle_config.get("shadow") is not None:
                files["caption_config_shadow_blur"] = (None, str(subtitle_config["shadow"]))
            
            if subtitle_config.get("max_lines"):
                files["caption_config_line_count"] = (None, str(subtitle_config["max_lines"]))
                
            if subtitle_config.get("max_length"):
                files["caption_config_line_max_length"] = (None, str(subtitle_config["max_length"]))
            
            # Map alignment int to string
            align = subtitle_config.get("alignment", 2)
            if align == 2:
                files["caption_config_subtitle_position"] = (None, "bottom")
            elif align == 5:
                files["caption_config_subtitle_position"] = (None, "top")
            elif align == 10:
                files["caption_config_subtitle_position"] = (None, "center")
            else:
                files["caption_config_subtitle_position"] = (None, "bottom")

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
        self, image_id: str, tts_id: str, text: str, subtitle_config: dict | None = None
    ) -> GeneratedVideo:
        """
        Generate video with captions (synchronous operation).

        Args:
            image_id: Background image file_id
            tts_id: TTS audio file_id
            text: Text for captions
            subtitle_config: Optional subtitle styling configuration

        Returns:
            GeneratedVideo with file_id
        """
        file_id = await self.start_captioned_video_generation(image_id, tts_id, text, subtitle_config)
        return GeneratedVideo(file_id=file_id, tts_id=tts_id, image_id=image_id)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def start_video_merge(
        self,
        video_ids: list[str],
        background_music_id: str | None = None,
        music_volume: float | None = None
    ) -> str:
        """
        Start merging multiple videos with optional background music.

        Args:
            video_ids: List of video file_ids to merge
            background_music_id: Optional background music file_id
            music_volume: Optional music volume (0.0-1.0)

        Returns:
            file_id (synchronous response)
        """
        # Use local execution if enabled
        if self.execution_mode == "local":
            return self._merge_videos_local(video_ids, background_music_id, music_volume)

        logger.info(f"Starting video merge: {len(video_ids)} videos")

        # Convert list to comma-separated string and use files= for multipart/form-data
        files = {"video_ids": (None, ",".join(video_ids))}

        if background_music_id:
            files["background_music_id"] = (None, background_music_id)
            volume = music_volume if music_volume is not None else 0.1
            files["background_music_volume"] = (None, str(volume))

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
        self,
        video_ids: list[str],
        background_music_id: str | None = None,
        background_music_path: str | None = None,
        music_volume: float | None = None
    ) -> str:
        """
        Merge videos (synchronous operation).

        Args:
            video_ids: List of video file_ids to merge
            background_music_id: Optional background music file_id (deprecated, use background_music_path)
            background_music_path: Optional background music file_id or local path
            music_volume: Optional music volume (0.0-1.0)

        Returns:
            Final merged video file_id
        """
        # Use background_music_path if provided, otherwise fall back to background_music_id
        music_id = background_music_path or background_music_id

        # Upload background music if it's a local path
        if music_id:
            music_id = await self.upload_local_file_if_needed(music_id, "audio")

        file_id = await self.start_video_merge(video_ids, music_id, music_volume)
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
        return f"{self.base_url}/api/v1/media/storage/{file_id}"

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

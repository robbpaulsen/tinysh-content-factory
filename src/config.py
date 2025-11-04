"""Configuration management using pydantic-settings."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    google_api_key: str = Field(..., description="Google Gemini API key")
    together_api_key: str = Field(..., description="Together.ai API key")

    # Google Credentials
    google_credentials_path: Path = Field(
        default=Path("credentials.json"),
        description="Path to Google OAuth credentials JSON"
    )

    # Media Server
    media_server_url: str = Field(
        default="http://localhost:8000",
        description="Local media processing server URL"
    )

    # Workflow Configuration
    subreddit: str = Field(default="selfimprovement", description="Reddit subreddit to scrape")
    content_type: str = Field(
        default="motivational speech",
        description="Type of content to generate"
    )
    art_style: str = Field(
        default="Create a cinematic image in a dramatic, high-contrast photographic style...",
        description="Art style for image generation"
    )

    # Google Sheets
    google_sheet_id: str = Field(..., description="Google Sheets document ID")
    sheet_name: str = Field(default="Sheet1", description="Sheet name within the document")

    # TTS Configuration
    tts_engine: Literal["kokoro", "chatterbox"] = Field(
        default="kokoro",
        description="TTS engine to use"
    )
    kokoro_voice: str = Field(default="af_bella", description="Kokoro voice name")
    kokoro_speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Kokoro speech speed")

    # Chatterbox TTS
    chatterbox_exaggeration: float = Field(default=0.5, description="Chatterbox exaggeration")
    chatterbox_cfg_weight: float = Field(default=0.5, description="Chatterbox CFG weight")
    chatterbox_temperature: float = Field(default=0.8, description="Chatterbox temperature")
    chatterbox_voice_sample_id: str | None = Field(
        default=None,
        description="File ID for voice cloning"
    )

    # Background Music
    background_music_id: str | None = Field(
        default=None,
        description="File ID of background music"
    )
    background_music_volume: float = Field(
        default=0.2,
        ge=0.1,
        le=1.0,
        description="Background music volume"
    )

    # Image Generation
    flux_model: str = Field(
        default="black-forest-labs/FLUX.1-schnell-Free",
        description="FLUX model to use"
    )
    image_width: int = Field(default=768, description="Generated image width")
    image_height: int = Field(default=1344, description="Generated image height")

    # YouTube
    youtube_privacy_status: Literal["public", "private", "unlisted"] = Field(
        default="public",
        description="YouTube video privacy status"
    )
    youtube_category_id: str = Field(
        default="24",
        description="YouTube video category (24=Entertainment)"
    )

    # Retry Configuration
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, description="Initial retry delay in seconds")

    # Timeouts
    http_timeout: float = Field(default=30.0, description="HTTP request timeout in seconds")
    media_processing_timeout: float = Field(
        default=300.0,
        description="Media processing timeout in seconds"
    )

    # FFmpeg Optimization
    ffmpeg_encoder: Literal["nvenc", "x264", "auto"] = Field(
        default="auto",
        description="Video encoder (nvenc=GPU, x264=CPU, auto=detect)"
    )
    ffmpeg_preset: str = Field(
        default="p4",
        description="NVENC preset (p1-p7) or x264 preset (ultrafast, fast, medium, slow)"
    )
    ffmpeg_cq: int = Field(
        default=23,
        ge=18,
        le=28,
        description="Video quality (18=best, 28=worst)"
    )
    ffmpeg_bitrate: str = Field(
        default="5M",
        description="Target video bitrate (e.g., 5M, 8M)"
    )
    ffmpeg_audio_bitrate: str = Field(
        default="128k",
        description="Audio bitrate (e.g., 128k, 192k)"
    )

    # Parallelization
    parallel_image_generation: bool = Field(
        default=False,
        description="Generate all images in parallel (recommended)"
    )
    max_parallel_images: int = Field(
        default=8,
        ge=1,
        le=20,
        description="Maximum simultaneous image generations"
    )


# Global settings instance
settings = Settings()

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
        default=Path(".credentials/credentials.json"),
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

    # Profile System (replaces individual voice/music settings)
    active_profile: str | None = Field(
        default=None,
        description="Active profile name (uses default from config/profiles.yaml if None)"
    )
    profiles_path: Path = Field(
        default=Path("config/profiles.yaml"),
        description="Path to profiles configuration file"
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
        default="private",
        description="YouTube video privacy status (default: private for scheduling)"
    )
    youtube_category_id: str = Field(
        default="22",
        description="YouTube video category (22=People & Blogs)"
    )
    youtube_timezone: str = Field(
        default="America/Chicago",
        description="Timezone for scheduling (e.g., America/Chicago, America/New_York)"
    )
    youtube_schedule_start_hour: int = Field(
        default=6,
        ge=0,
        le=23,
        description="First video publish hour (24h format, default: 6 = 6 AM)"
    )
    youtube_schedule_end_hour: int = Field(
        default=16,
        ge=0,
        le=23,
        description="Last video publish hour (24h format, default: 16 = 4 PM)"
    )
    youtube_schedule_interval_hours: int = Field(
        default=2,
        ge=1,
        le=12,
        description="Hours between video publishes (default: 2)"
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

    # SEO Optimization
    seo_enabled: bool = Field(
        default=True,
        description="Enable SEO metadata generation with Gemini"
    )

    # Logging
    log_to_file: bool = Field(
        default=True,
        description="Enable logging to file with rotation"
    )
    log_dir: Path = Field(
        default=Path("output/logs"),
        description="Directory for log files"
    )
    log_max_age_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Maximum age of log files to keep (days)"
    )


# Global settings instance
settings = Settings()

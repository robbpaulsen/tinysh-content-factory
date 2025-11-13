"""Channel configuration management for multi-channel system."""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class ContentSettings(BaseModel):
    """Content generation settings."""

    format: str  # shorts, video, compilation_video
    duration_range: list[int]
    subreddit: str | None = None
    backup_subreddits: list[str] = Field(default_factory=list)
    content_type: str | None = None
    topics: list[str] = Field(default_factory=list)
    compilation_type: str | None = None


class VideoSettings(BaseModel):
    """Video format settings."""

    aspect_ratio: str  # 9:16, 16:9
    width: int
    height: int


class SceneSettings(BaseModel):
    """Scene configuration."""

    count_range: list[int]


class ImageSettings(BaseModel):
    """Image generation settings."""

    model: str
    style: str


class YouTubeScheduleSettings(BaseModel):
    """YouTube upload schedule settings."""

    videos_per_day: int
    start_hour: int
    end_hour: int
    interval_hours: int
    timezone: str


class YouTubeSettings(BaseModel):
    """YouTube upload settings."""

    category_id: str
    made_for_kids: bool
    schedule: YouTubeScheduleSettings
    default_tags: list[str]


class SEOSettings(BaseModel):
    """SEO optimization settings."""

    enabled: bool
    channel_name: str
    target_audience: str
    primary_keywords: list[str]


class CompilationSettings(BaseModel):
    """Compilation video settings."""

    clips_per_video: list[int]
    clip_duration_max: int
    transitions: str
    add_text_overlays: bool
    add_intro: bool
    add_outro: bool


class YouTubeDownloadSettings(BaseModel):
    """YouTube video download settings."""

    search_queries: list[str]
    max_results_per_query: int
    min_views: int
    max_days_old: int | None = None
    download_format: str


class ChannelConfigModel(BaseModel):
    """Channel configuration model."""

    name: str
    description: str
    handle: str
    channel_type: str  # ai_generated_shorts, ai_generated_videos, youtube_compilation
    content: ContentSettings
    video: VideoSettings
    scenes: SceneSettings | None = None
    image: ImageSettings | None = None
    youtube: YouTubeSettings
    seo: SEOSettings
    default_profile: str | None = None
    profiles_path: str | None = "profiles.yaml"
    compilation: CompilationSettings | None = None
    youtube_download: YouTubeDownloadSettings | None = None


class ChannelConfig:
    """Channel configuration loader and manager."""

    def __init__(self, channel_name: str):
        """
        Initialize channel configuration.

        Args:
            channel_name: Name of the channel directory (e.g., "momentum_mindset")
        """
        self.channel_name = channel_name
        self.channel_dir = Path("channels") / channel_name

        if not self.channel_dir.exists():
            raise FileNotFoundError(
                f"Channel directory not found: {self.channel_dir}. "
                f"Available channels: {self.list_available_channels()}"
            )

        self.config = self._load_config()
        logger.info(f"Loaded configuration for channel: {self.config.name}")

    def _load_config(self) -> ChannelConfigModel:
        """Load and validate channel configuration from YAML."""
        config_path = self.channel_dir / "channel.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Validate with Pydantic
            config = ChannelConfigModel(**data)
            return config

        except ValidationError as e:
            logger.error(f"Invalid channel configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading channel config: {e}")
            raise

    @staticmethod
    def list_available_channels() -> list[str]:
        """List all available channels."""
        channels_dir = Path("channels")
        if not channels_dir.exists():
            return []

        channels = []
        for path in channels_dir.iterdir():
            if path.is_dir() and (path / "channel.yaml").exists():
                channels.append(path.name)

        return sorted(channels)

    @property
    def output_dir(self) -> Path:
        """Get output directory for this channel."""
        return self.channel_dir / "output"

    @property
    def prompts_dir(self) -> Path:
        """Get prompts directory for this channel."""
        return self.channel_dir / "prompts"

    @property
    def assets_dir(self) -> Path:
        """Get assets directory for this channel."""
        return self.channel_dir / "assets"

    @property
    def credentials_path(self) -> Path:
        """Get Google OAuth credentials path."""
        return self.channel_dir / "credentials.json"

    @property
    def youtube_token_path(self) -> Path:
        """Get YouTube token path."""
        return self.channel_dir / "token_youtube.json"

    @property
    def profiles_path(self) -> Path:
        """Get profiles.yaml path."""
        if self.config.profiles_path:
            return self.channel_dir / self.config.profiles_path
        return self.channel_dir / "profiles.yaml"

    def get_prompt(self, prompt_type: str) -> str | None:
        """
        Load prompt from prompts directory.

        Args:
            prompt_type: Type of prompt (script, image, seo, metadata)

        Returns:
            Prompt text or None if not found
        """
        prompt_file = self.prompts_dir / f"{prompt_type}.txt"

        if not prompt_file.exists():
            logger.warning(f"Prompt file not found: {prompt_file}")
            return None

        try:
            with open(prompt_file, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading prompt file {prompt_file}: {e}")
            return None

    def is_ai_generated(self) -> bool:
        """Check if channel uses AI generation."""
        return self.config.channel_type in ["ai_generated_shorts", "ai_generated_videos"]

    def is_compilation(self) -> bool:
        """Check if channel is compilation-based."""
        return self.config.channel_type == "youtube_compilation"

    def get_subreddits(self) -> list[str]:
        """Get list of subreddits for content sourcing."""
        subreddits = []
        if self.config.content.subreddit:
            subreddits.append(self.config.content.subreddit)
        subreddits.extend(self.config.content.backup_subreddits)
        return subreddits

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ChannelConfig(name='{self.config.name}', "
            f"type='{self.config.channel_type}', "
            f"handle='{self.config.handle}')"
        )

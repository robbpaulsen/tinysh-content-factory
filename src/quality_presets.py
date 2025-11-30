"""
Quality presets for content generation.

Provides different quality levels to balance speed vs quality:
- Draft: Fast testing (4x faster)
- Preview: Balanced preview (2x faster)
- Production: Full quality (current default)
"""

from dataclasses import dataclass
from typing import Literal

QualityLevel = Literal["draft", "preview", "production"]


@dataclass
class ImagePreset:
    """Image generation preset configuration."""

    width: int
    height: int
    steps: int
    description: str


@dataclass
class TTSPreset:
    """TTS generation preset configuration."""

    speed: float
    description: str


@dataclass
class VideoPreset:
    """Video encoding preset configuration."""

    video_bitrate: str
    audio_bitrate: str
    preset: str  # FFmpeg preset (ultrafast, fast, medium, slow)
    description: str


@dataclass
class QualityPreset:
    """Complete quality preset configuration."""

    name: str
    image: ImagePreset
    tts: TTSPreset
    video: VideoPreset
    description: str


# Quality Preset Definitions
QUALITY_PRESETS: dict[QualityLevel, QualityPreset] = {
    "draft": QualityPreset(
        name="Draft",
        description="Fast testing mode - 4x faster, low quality",
        image=ImagePreset(
            width=256,
            height=256,
            steps=1,
            description="Tiny images, single step generation",
        ),
        tts=TTSPreset(
            speed=1.5,
            description="1.5x speed - faster but less natural",
        ),
        video=VideoPreset(
            video_bitrate="500k",
            audio_bitrate="64k",
            preset="ultrafast",
            description="Ultra-fast encoding, low bitrate",
        ),
    ),
    "preview": QualityPreset(
        name="Preview",
        description="Balanced mode - 2x faster, medium quality",
        image=ImagePreset(
            width=512,
            height=512,
            steps=2,
            description="Medium images, quick generation",
        ),
        tts=TTSPreset(
            speed=1.2,
            description="1.2x speed - slightly faster",
        ),
        video=VideoPreset(
            video_bitrate="2000k",
            audio_bitrate="128k",
            preset="fast",
            description="Fast encoding, medium bitrate",
        ),
    ),
    "production": QualityPreset(
        name="Production",
        description="Full quality mode - current default",
        image=ImagePreset(
            width=1080,
            height=1920,
            steps=4,
            description="Full vertical video resolution",
        ),
        tts=TTSPreset(
            speed=1.0,
            description="Normal speed - natural sounding",
        ),
        video=VideoPreset(
            video_bitrate="5000k",
            audio_bitrate="192k",
            preset="medium",
            description="High quality encoding",
        ),
    ),
}


def get_preset(level: QualityLevel = "production") -> QualityPreset:
    """
    Get quality preset by level.

    Args:
        level: Quality level (draft, preview, or production)

    Returns:
        QualityPreset configuration

    Raises:
        ValueError: If level is invalid
    """
    if level not in QUALITY_PRESETS:
        raise ValueError(
            f"Invalid quality level: {level}. "
            f"Must be one of: {', '.join(QUALITY_PRESETS.keys())}"
        )
    return QUALITY_PRESETS[level]


def get_image_dimensions(level: QualityLevel = "production") -> tuple[int, int]:
    """
    Get image dimensions for quality level.

    Args:
        level: Quality level

    Returns:
        (width, height) tuple
    """
    preset = get_preset(level)
    return (preset.image.width, preset.image.height)


def get_tts_speed(level: QualityLevel = "production") -> float:
    """
    Get TTS speed multiplier for quality level.

    Args:
        level: Quality level

    Returns:
        Speed multiplier (1.0 = normal)
    """
    preset = get_preset(level)
    return preset.tts.speed


def list_presets() -> dict[str, str]:
    """
    List all available presets with descriptions.

    Returns:
        Dict mapping preset names to descriptions
    """
    return {
        level: preset.description
        for level, preset in QUALITY_PRESETS.items()
    }


def get_speed_improvement(level: QualityLevel) -> float:
    """
    Estimate speed improvement factor compared to production.

    Args:
        level: Quality level

    Returns:
        Speed improvement factor (e.g., 4.0 = 4x faster)
    """
    if level == "production":
        return 1.0

    preset = get_preset(level)
    prod_preset = get_preset("production")

    # Estimate based on:
    # - Image resolution (area reduction)
    # - TTS speed multiplier
    # - Video encoding preset
    image_area_ratio = (
        (prod_preset.image.width * prod_preset.image.height)
        / (preset.image.width * preset.image.height)
    )

    tts_ratio = prod_preset.tts.speed / preset.tts.speed

    # Video encoding speed varies:
    # ultrafast: 4x faster than medium
    # fast: 2x faster than medium
    video_speed = {
        "ultrafast": 4.0,
        "fast": 2.0,
        "medium": 1.0,
    }.get(preset.video.preset, 1.0)

    # Weighted average (image generation is usually the bottleneck)
    # 60% image, 20% TTS, 20% video
    estimated_speed = (
        0.6 * image_area_ratio + 0.2 * tts_ratio + 0.2 * video_speed
    ) / 3

    return round(estimated_speed, 1)

"""Profile Manager for voice and music configurations."""

import logging
import random
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class VoiceConfig(BaseModel):
    """Voice configuration for a profile."""

    engine: Literal["chatterbox", "kokoro"] = Field(
        ..., description="TTS engine to use"
    )

    # Chatterbox settings
    sample_path: str | None = Field(
        None, description="Path to voice sample (Chatterbox only)"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Chatterbox temperature"
    )
    cfg_weight: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Chatterbox CFG weight"
    )
    exaggeration: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Chatterbox exaggeration"
    )

    # Kokoro settings
    voice: str | None = Field(
        None, description="Kokoro voice name (e.g., af_bella)"
    )
    speed: float = Field(
        default=1.0, ge=0.5, le=2.0, description="Kokoro speech speed"
    )

    @field_validator("sample_path")
    @classmethod
    def validate_sample_path(cls, v: str | None, info) -> str | None:
        """Validate voice sample path exists for Chatterbox."""
        if v and info.data.get("engine") == "chatterbox":
            path = Path(v)
            if not path.exists():
                logger.warning(
                    f"Voice sample path does not exist: {v}. "
                    "Voice cloning may fail."
                )
        return v


class MusicTrack(BaseModel):
    """Individual music track in a playlist."""

    path: str = Field(..., description="Path to music file")
    name: str = Field(..., description="Friendly name for the track")

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate music file path exists."""
        path = Path(v)
        if not path.exists():
            logger.warning(
                f"Music file does not exist: {v}. "
                "Video generation may fail if this track is selected."
            )
        return v


class MusicConfig(BaseModel):
    """Music configuration for a profile."""

    playlist: list[MusicTrack] = Field(
        ..., description="List of music tracks to rotate through"
    )
    volume: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Background music volume"
    )
    rotation: Literal["random", "sequential"] = Field(
        default="random", description="Music selection mode"
    )


class Profile(BaseModel):
    """Complete profile configuration."""

    name: str = Field(..., description="Profile display name")
    description: str = Field(
        default="", description="Profile description"
    )
    voice: VoiceConfig = Field(..., description="Voice settings")
    music: MusicConfig = Field(..., description="Music settings")


class ProfileManager:
    """Manages voice and music profiles from YAML configuration."""

    def __init__(self, profiles_path: str | Path = "profiles.yaml"):
        """
        Initialize profile manager.

        Args:
            profiles_path: Path to profiles YAML file
        """
        self.profiles_path = Path(profiles_path)
        self.profiles: dict[str, Profile] = {}
        self.default_profile: str = ""
        self.rotation_state: dict[str, int] = {}

        self._load_profiles()

    def _load_profiles(self):
        """Load profiles from YAML file."""
        if not self.profiles_path.exists():
            raise FileNotFoundError(
                f"Profiles file not found: {self.profiles_path}. "
                "Create profiles.yaml in project root."
            )

        logger.info(f"Loading profiles from {self.profiles_path}")

        with open(self.profiles_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Load profiles
        profiles_data = data.get("profiles", {})
        for profile_id, profile_data in profiles_data.items():
            try:
                self.profiles[profile_id] = Profile(**profile_data)
                logger.debug(f"Loaded profile: {profile_id}")
            except Exception as e:
                logger.error(
                    f"Failed to load profile '{profile_id}': {e}"
                )
                raise

        # Load default profile
        self.default_profile = data.get("default_profile", "")
        if self.default_profile not in self.profiles:
            available = list(self.profiles.keys())
            raise ValueError(
                f"Default profile '{self.default_profile}' not found. "
                f"Available profiles: {available}"
            )

        # Load rotation state
        self.rotation_state = data.get("rotation_state", {})
        # Initialize missing states
        for profile_id in self.profiles:
            if profile_id not in self.rotation_state:
                self.rotation_state[profile_id] = 0

        logger.info(
            f"Loaded {len(self.profiles)} profiles. "
            f"Default: {self.default_profile}"
        )

    def get_profile(self, profile_id: str | None = None) -> Profile:
        """
        Get a profile by ID or return default.

        Args:
            profile_id: Profile identifier (uses default if None)

        Returns:
            Profile configuration

        Raises:
            ValueError: If profile_id not found
        """
        if profile_id is None:
            profile_id = self.default_profile

        if profile_id not in self.profiles:
            available = list(self.profiles.keys())
            raise ValueError(
                f"Profile '{profile_id}' not found. "
                f"Available: {available}"
            )

        return self.profiles[profile_id]

    def select_music(self, profile_id: str | None = None) -> MusicTrack:
        """
        Select a music track from profile's playlist.

        Args:
            profile_id: Profile identifier (uses default if None)

        Returns:
            Selected music track

        Raises:
            ValueError: If playlist is empty
        """
        profile = self.get_profile(profile_id)
        if profile_id is None:
            profile_id = self.default_profile

        playlist = profile.music.playlist
        if not playlist:
            raise ValueError(
                f"Profile '{profile_id}' has no music in playlist"
            )

        # Select based on rotation mode
        if profile.music.rotation == "random":
            track = random.choice(playlist)
            logger.info(
                f"Selected random music: {track.name} "
                f"from profile '{profile_id}'"
            )
        else:  # sequential
            index = self.rotation_state.get(profile_id, 0)
            track = playlist[index % len(playlist)]
            # Update rotation state for next time
            self.rotation_state[profile_id] = (index + 1) % len(playlist)
            self._save_rotation_state()
            logger.info(
                f"Selected sequential music ({index + 1}/{len(playlist)}): "
                f"{track.name} from profile '{profile_id}'"
            )

        return track

    def _save_rotation_state(self):
        """Save rotation state back to YAML file."""
        try:
            with open(self.profiles_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            data["rotation_state"] = self.rotation_state

            with open(self.profiles_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            logger.debug("Saved rotation state to profiles.yaml")
        except Exception as e:
            logger.warning(f"Failed to save rotation state: {e}")

    def list_profiles(self) -> dict[str, str]:
        """
        List all available profiles.

        Returns:
            Dict of profile_id -> profile name
        """
        return {
            profile_id: profile.name
            for profile_id, profile in self.profiles.items()
        }

    def get_voice_config(self, profile_id: str | None = None) -> dict[str, Any]:
        """
        Get voice configuration as dict for MediaService.

        Args:
            profile_id: Profile identifier (uses default if None)

        Returns:
            Voice config dict ready for TTS generation
        """
        profile = self.get_profile(profile_id)
        voice = profile.voice

        config = {"engine": voice.engine}

        if voice.engine == "chatterbox":
            config.update({
                "sample_path": voice.sample_path,
                "temperature": voice.temperature,
                "cfg_weight": voice.cfg_weight,
                "exaggeration": voice.exaggeration,
            })
        elif voice.engine == "kokoro":
            config.update({
                "voice": voice.voice or "af_bella",
                "speed": voice.speed,
            })

        return config

    def get_music_config(self, profile_id: str | None = None) -> dict[str, Any]:
        """
        Get music configuration with selected track.

        Args:
            profile_id: Profile identifier (uses default if None)

        Returns:
            Music config dict with selected track and volume
        """
        profile = self.get_profile(profile_id)
        track = self.select_music(profile_id)

        return {
            "path": track.path,
            "name": track.name,
            "volume": profile.music.volume,
        }

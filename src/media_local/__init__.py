"""Local media processing - eliminates Docker dependency.

This package provides local implementations of media processing:
- TTS: Chatterbox (voice cloning) + Kokoro (fallback)
- Video: FFmpeg wrapper for video generation and merging
- Storage: Local file management

Benefits over Docker:
- Faster execution (no HTTP overhead)
- Easier debugging (direct Python)
- Full code control (no container restarts)
- Better collaborative development
"""

from src.media_local.config import device, get_device_info

# Optional imports - only available if dependencies installed
__all__ = ["device", "get_device_info"]

try:
    from src.media_local.tts.chatterbox import ChatterboxTTS

    __all__.append("ChatterboxTTS")
except ImportError:
    pass

try:
    from src.media_local.video.builder import VideoBuilder

    __all__.append("VideoBuilder")
except ImportError:
    pass

try:
    from src.media_local.storage.manager import StorageManager

    __all__.append("StorageManager")
except ImportError:
    pass

"""Application-wide constants and magic numbers.

Centralizes configuration values and magic numbers for easier maintenance.
"""

# Polling intervals (seconds)
# ⚠️ CRITICAL: Do not reduce these values to avoid API rate limits
POLL_INTERVAL_FILE_READY = 0.5  # Local file operations (fast)
POLL_INTERVAL_TTS = 15.0  # TTS generation (slow, rate-limited)
POLL_INTERVAL_VIDEO = 2.0  # Video processing
POLL_INTERVAL_DEFAULT = 2.0  # Generic processing tasks

# Timeouts (seconds)
TIMEOUT_FILE_READY = 60.0  # Wait for file to be ready
TIMEOUT_TTS_GENERATION = 120.0  # TTS can take up to 2 minutes
TIMEOUT_VIDEO_GENERATION = 300.0  # Video can take up to 5 minutes
TIMEOUT_HTTP_DEFAULT = 30.0  # Standard HTTP request timeout

# Together.ai FLUX API
FLUX_RATE_LIMIT_PER_MINUTE = 6  # Free tier: 6 images per minute
FLUX_RATE_LIMIT_WINDOW = 60  # Time window in seconds

# Gemini token calculation
GEMINI_TOKENS_PER_SECOND = 32  # 32 tokens = 1 second of speech
GEMINI_MIN_DURATION_SECONDS = 15  # Minimum video duration
GEMINI_MAX_DURATION_SECONDS = 45  # Maximum video duration (Shorts optimal)
GEMINI_MIN_TOKENS = GEMINI_MIN_DURATION_SECONDS * GEMINI_TOKENS_PER_SECOND  # 480
GEMINI_MAX_TOKENS = GEMINI_MAX_DURATION_SECONDS * GEMINI_TOKENS_PER_SECOND  # 1440

# Retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_MIN_WAIT = 2  # Minimum wait between retries (seconds)
DEFAULT_RETRY_MAX_WAIT = 10  # Maximum wait between retries (seconds)

# File management
LOG_ROTATION_SIZE = "10 MB"  # Rotate logs at 10MB
LOG_RETENTION_DAYS = "7 days"  # Keep logs for 7 days

__all__ = [
    # Polling
    "POLL_INTERVAL_FILE_READY",
    "POLL_INTERVAL_TTS",
    "POLL_INTERVAL_VIDEO",
    "POLL_INTERVAL_DEFAULT",
    # Timeouts
    "TIMEOUT_FILE_READY",
    "TIMEOUT_TTS_GENERATION",
    "TIMEOUT_VIDEO_GENERATION",
    "TIMEOUT_HTTP_DEFAULT",
    # FLUX API
    "FLUX_RATE_LIMIT_PER_MINUTE",
    "FLUX_RATE_LIMIT_WINDOW",
    # Gemini
    "GEMINI_TOKENS_PER_SECOND",
    "GEMINI_MIN_DURATION_SECONDS",
    "GEMINI_MAX_DURATION_SECONDS",
    "GEMINI_MIN_TOKENS",
    "GEMINI_MAX_TOKENS",
    # Retry
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_MIN_WAIT",
    "DEFAULT_RETRY_MAX_WAIT",
    # Files
    "LOG_ROTATION_SIZE",
    "LOG_RETENTION_DAYS",
]

"""Speech-to-Text using Faster Whisper - Ported from server/video/stt.py

Provides accurate speech recognition with word-level timestamps.
"""

from faster_whisper import WhisperModel
from loguru import logger

from src.media_local.config import device, whisper_model, whisper_compute_type


class STT:
    """Speech-to-Text transcription using Faster Whisper."""

    def __init__(self):
        self.model = WhisperModel(
            model_size_or_path=whisper_model,
            compute_type=whisper_compute_type
        )

    def transcribe(self, audio_path, language=None, beam_size=5):
        """
        Transcribe audio to text with word-level timestamps.

        Args:
            audio_path: Path to audio file or file-like object
            language: Optional language code (e.g., 'en', 'es')
            beam_size: Beam search size for decoding

        Returns:
            Tuple of (captions, duration) where captions is a list of dicts with:
                - text: The word text
                - start_ts: Start timestamp in seconds
                - end_ts: End timestamp in seconds
        """
        device_str = device.type if hasattr(device, 'type') else str(device)
        logger.bind(
            device=device_str,
            model_size=whisper_model,
            compute_type=whisper_compute_type,
            audio_path=audio_path,
            language=language,
        ).debug(
            "transcribing audio with Whisper model",
        )
        segments, info = self.model.transcribe(
            audio_path,
            beam_size=beam_size,
            word_timestamps=True,
            language=language,
        )

        duration = info.duration
        captions = []
        for segment in segments:
            for word in segment.words:
                captions.append(
                    {
                        "text": word.word,
                        "start_ts": word.start,
                        "end_ts": word.end,
                    }
                )
        return captions, duration


__all__ = ["STT"]

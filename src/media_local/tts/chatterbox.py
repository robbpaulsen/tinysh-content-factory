"""Chatterbox TTS engine for voice cloning.

Ported from server-code-and-layout/video/tts_chatterbox.py

PRIORITY: This is the primary TTS engine for voice cloning.
Kokoro TTS is only a fallback for generic voices.
"""

import os
import time
import traceback
import warnings
from pathlib import Path
from typing import Optional

import nltk
import torch
import torchaudio as ta
from loguru import logger

from src.media_local.config import TORCH_AVAILABLE, device

# Suppress PyTorch warnings
warnings.filterwarnings("ignore")

# Try to import ChatterboxTTS
try:
    from chatterbox.tts import ChatterboxTTS as ChatterboxModel

    CHATTERBOX_AVAILABLE = True
except ImportError:
    CHATTERBOX_AVAILABLE = False
    logger.warning(
        "Chatterbox TTS not available - voice cloning disabled. "
        "Install with: uv pip install chatterbox-tts"
    )


class ChatterboxTTS:
    """Chatterbox TTS with voice cloning support."""

    def __init__(self):
        """Initialize ChatterboxTTS and ensure NLTK data is available."""
        if not TORCH_AVAILABLE:
            raise RuntimeError(
                "PyTorch not available - required for Chatterbox TTS. "
                "Install with: uv pip install torch torchaudio"
            )

        if not CHATTERBOX_AVAILABLE:
            raise RuntimeError(
                "Chatterbox TTS not available - required for voice cloning. "
                "Install with: uv pip install chatterbox-tts"
            )

        self.ensure_nltk_data()
        logger.debug("ChatterboxTTS initialized")

    def ensure_nltk_data(self):
        """Ensure NLTK punkt tokenizer is available."""
        try:
            nltk.data.find("tokenizers/punkt")
            nltk.data.find("tokenizers/punkt_tab")
            logger.debug("NLTK punkt tokenizer found")
        except LookupError:
            logger.debug("Downloading NLTK punkt tokenizer...")
            try:
                nltk.download("punkt", quiet=True)
                nltk.download("punkt_tab", quiet=True)
                logger.debug("NLTK punkt tokenizer downloaded successfully")
            except Exception as e:
                logger.error(f"Failed to download NLTK punkt tokenizer: {e}")
                raise

    def split_text_into_chunks(
        self, text: str, max_chars_per_chunk: int = 300
    ) -> list[str]:
        """Split text into chunks respecting sentence boundaries.

        Args:
            text: Text to split
            max_chars_per_chunk: Maximum characters per chunk (default 300)

        Returns:
            List of text chunks
        """
        try:
            sentences = nltk.sent_tokenize(text)
            # Filter out empty sentences
            sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

            chunks = []
            current_chunk = ""

            for sentence in sentences:
                # If adding this sentence would exceed limit, finalize current chunk
                if (
                    current_chunk
                    and len(current_chunk) + len(sentence) + 1 > max_chars_per_chunk
                ):
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Add sentence to current chunk
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence

            # Add the last chunk
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            logger.debug(
                f"Text split into {len(chunks)} chunks (max {max_chars_per_chunk} chars each, preserving sentences)"
            )
            return chunks
        except Exception as e:
            logger.error(f"Error splitting text: {e}")
            # Fallback: return original text as single chunk
            return [text]

    def generate_audio_chunk(
        self,
        text_chunk: str,
        model: ChatterboxModel,
        audio_prompt_path: Optional[str] = None,
        temperature: float = 0.8,
        cfg_weight: float = 0.5,
        exaggeration: float = 0.5,
    ) -> Optional[torch.Tensor]:
        """Generate audio tensor for a single text chunk.

        Args:
            text_chunk: Text to generate audio for
            model: ChatterboxTTS model instance
            audio_prompt_path: Optional voice sample for cloning
            temperature: Temperature parameter (default 0.8)
            cfg_weight: CFG weight parameter (default 0.5)
            exaggeration: Exaggeration parameter (default 0.5)

        Returns:
            Audio tensor or None if generation failed
        """
        try:
            logger.debug(f"Generating audio for chunk: {text_chunk[:50]}...")

            # Check if audio prompt exists
            effective_prompt_path = None
            if audio_prompt_path and os.path.exists(audio_prompt_path):
                effective_prompt_path = audio_prompt_path
            elif audio_prompt_path:
                logger.warning(f"Audio prompt path not found: {audio_prompt_path}")

            # Generate audio
            wav_tensor = model.generate(
                text_chunk,
                audio_prompt_path=effective_prompt_path,
                temperature=temperature,
                cfg_weight=cfg_weight,
                exaggeration=exaggeration,
            )

            # Ensure tensor is on CPU and properly shaped
            wav_tensor_cpu = wav_tensor.cpu().float()

            # Ensure tensor is 2D: [channels, samples]
            if wav_tensor_cpu.ndim == 1:
                wav_tensor_cpu = wav_tensor_cpu.unsqueeze(0)
            elif wav_tensor_cpu.ndim > 2:
                logger.warning(
                    f"Unexpected tensor shape {wav_tensor_cpu.shape}, attempting to fix"
                )
                wav_tensor_cpu = wav_tensor_cpu.squeeze()
                if wav_tensor_cpu.ndim == 1:
                    wav_tensor_cpu = wav_tensor_cpu.unsqueeze(0)
                elif wav_tensor_cpu.ndim != 2 or wav_tensor_cpu.shape[0] != 1:
                    logger.error(
                        f"Could not reshape tensor {wav_tensor.shape} to [1, N]"
                    )
                    return None

            return wav_tensor_cpu

        except Exception as e:
            logger.error(f"Error generating audio chunk: {e}")
            logger.error(traceback.format_exc())
            return None

    def text_to_speech_pipeline(
        self,
        text: str,
        model: ChatterboxModel,
        max_chars_per_chunk: int = 1024,
        inter_chunk_silence_ms: int = 350,
        audio_prompt_path: Optional[str] = None,
        temperature: float = 0.8,
        cfg_weight: float = 0.5,
        exaggeration: float = 0.5,
    ) -> Optional[torch.Tensor]:
        """Convert text to speech with chunking support.

        Args:
            text: Text to convert
            model: ChatterboxTTS model instance
            max_chars_per_chunk: Maximum characters per chunk (default 1024)
            inter_chunk_silence_ms: Silence between chunks in ms (default 350)
            audio_prompt_path: Optional voice sample for cloning
            temperature: Temperature parameter (default 0.8)
            cfg_weight: CFG weight parameter (default 0.5)
            exaggeration: Exaggeration parameter (default 0.5)

        Returns:
            Final audio tensor or None if generation failed
        """
        try:
            # Split text into chunks
            text_chunks = self.split_text_into_chunks(text, max_chars_per_chunk)

            if not text_chunks:
                logger.error("No text chunks to process")
                return None

            all_audio_tensors = []
            sample_rate = model.sr

            logger.debug(f"Processing {len(text_chunks)} chunks at {sample_rate} Hz")

            for i, chunk_text in enumerate(text_chunks):
                logger.debug(f"Processing chunk {i+1}/{len(text_chunks)}")

                chunk_tensor = self.generate_audio_chunk(
                    chunk_text,
                    model,
                    audio_prompt_path,
                    temperature,
                    cfg_weight,
                    exaggeration,
                )

                if chunk_tensor is None:
                    logger.warning(f"Skipping chunk {i+1} due to generation error")
                    continue

                all_audio_tensors.append(chunk_tensor)

                # Add silence between chunks (except after last chunk)
                if i < len(text_chunks) - 1 and inter_chunk_silence_ms > 0:
                    silence_samples = int(sample_rate * inter_chunk_silence_ms / 1000.0)
                    silence_tensor = torch.zeros(
                        (1, silence_samples),
                        dtype=chunk_tensor.dtype,
                        device=chunk_tensor.device,
                    )
                    all_audio_tensors.append(silence_tensor)

            if not all_audio_tensors:
                logger.error("No audio tensors generated")
                return None

            # Concatenate all audio tensors
            logger.debug("Concatenating audio tensors...")
            final_audio_tensor = torch.cat(all_audio_tensors, dim=1)

            logger.debug(f"Final audio shape: {final_audio_tensor.shape}")
            return final_audio_tensor

        except Exception as e:
            logger.error(f"Error in text-to-speech pipeline: {e}")
            logger.error(traceback.format_exc())
            return None

    def generate(
        self,
        text: str,
        output_path: str | Path,
        sample_audio_path: str | Path = None,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        temperature: float = 0.8,
        chunk_chars: int = 1024,
        chunk_silence_ms: int = 350,
    ) -> bool:
        """Generate TTS audio with Chatterbox (voice cloning).

        Args:
            text: Text to convert to speech
            output_path: Output audio file path (WAV)
            sample_audio_path: Optional voice sample for cloning
            exaggeration: Exaggeration parameter (default 0.5)
            cfg_weight: CFG weight parameter (default 0.5)
            temperature: Temperature parameter (default 0.8)
            chunk_chars: Maximum characters per chunk (default 1024)
            chunk_silence_ms: Silence between chunks in ms (default 350)

        Returns:
            bool: True if successful, False otherwise
        """
        start = time.time()
        context_logger = logger.bind(
            text_length=len(text),
            sample_audio_path=str(sample_audio_path) if sample_audio_path else None,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            temperature=temperature,
            model="ChatterboxTTS",
            language="en-US",
            device=device.type if hasattr(device, "type") else str(device),
        )
        context_logger.debug("Starting TTS generation with Chatterbox")

        try:
            # Load model
            model = ChatterboxModel.from_pretrained(
                device=device.type if hasattr(device, "type") else str(device)
            )

            # Generate audio
            if sample_audio_path:
                wav = self.text_to_speech_pipeline(
                    text,
                    model,
                    audio_prompt_path=str(sample_audio_path),
                    temperature=temperature,
                    cfg_weight=cfg_weight,
                    exaggeration=exaggeration,
                    max_chars_per_chunk=chunk_chars,
                    inter_chunk_silence_ms=chunk_silence_ms,
                )
            else:
                wav = self.text_to_speech_pipeline(
                    text,
                    model,
                    temperature=temperature,
                    cfg_weight=cfg_weight,
                    exaggeration=exaggeration,
                    max_chars_per_chunk=chunk_chars,
                    inter_chunk_silence_ms=chunk_silence_ms,
                )

            if wav is None:
                context_logger.error("Failed to generate audio")
                return False

            # Convert to stereo if needed
            if wav.dim() == 2 and wav.shape[0] == 1:
                wav = wav.repeat(2, 1)
            elif wav.dim() == 1:
                wav = wav.unsqueeze(0).repeat(2, 1)

            # Save audio
            audio_length = wav.shape[1] / model.sr
            ta.save(str(output_path), wav, model.sr)

            context_logger.bind(
                execution_time=time.time() - start,
                audio_length=audio_length,
                speedup=audio_length / (time.time() - start),
            ).debug("TTS generation with Chatterbox completed")

            return True

        except Exception as e:
            context_logger.bind(error=str(e)).error(
                "Error generating TTS with Chatterbox"
            )
            logger.error(traceback.format_exc())
            return False

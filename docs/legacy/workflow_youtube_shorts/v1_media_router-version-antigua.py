from fastapi import Query, Request, status, APIRouter, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Literal, Optional
from pydantic import BaseModel
import os
import shutil
import iso639
from loguru import logger
import matplotlib.font_manager as fm
from PIL import Image
from io import BytesIO

from video.ambient_video import createAmbientVideo
from video.audio_composer import AudioComposer, parse_ambient_config, extendAudio, extract_looping_audio
from video.caption import Caption
from video.media import MediaUtils
from video.builder import VideoBuilder
from video.audio_composer import AudioComposer
from utils.image import resize_image_cover
from video.config import download_chunk_size_mb, recursive_merge_max_files, merge_file_limit
from video.tts_alignment import tts_alignment, segment_from_word_timings, word_timings_to_captions
from utils.batch import batch_operation
from video.tts_chatterbox import chatterbox_supported_languages

# Import dependencies
from .dependencies import StorageDep, STTDep, TTSManagerDep, TTSChatterboxMultilingualDep, TTSChatterboxDep

CHUNK_SIZE = 1024 * 1024 * download_chunk_size_mb

def iterfile(path: str):
    with open(path, mode="rb") as file:
        while chunk := file.read(CHUNK_SIZE):
            yield chunk

v1_media_api_router = APIRouter()

@v1_media_api_router.post("/audio-tools/transcribe")
def transcribe(
    audio_file: UploadFile = File(..., description="Audio file to transcribe"),
    language: Optional[str] = Form(None, description="Language code (optional)"),
    stt: STTDep = None,
):
    """
    Transcribe audio file to text.
    """
    logger.bind(language=language, filename=audio_file.filename).info(
        "Transcribing audio file"
    )
    captions, duration = stt.transcribe(audio_file.file, beam_size=5, language=language)
    transcription = "".join([cap["text"] for cap in captions])

    return {
        "transcription": transcription,
        "duration": duration,
    }

@v1_media_api_router.get("/audio-tools/tts/kokoro/voices")
def get_kokoro_voices(tts_manager: TTSManagerDep = None):
    voices = tts_manager.valid_kokoro_voices()
    return {"voices": voices}

@v1_media_api_router.post("/audio-tools/tts/kokoro")
def generate_kokoro_tts(
    background_tasks: BackgroundTasks,
    text: str = Form(..., description="Text to convert to speech"),
    voice: Optional[str] = Form(None, description="Voice name for kokoro TTS"),
    speed: Optional[float] = Form(None, description="Speed for kokoro TTS"),
    storage: StorageDep = None,
    tts_manager: TTSManagerDep = None,
):
    """
    Generate audio from text using specified TTS engine.
    """
    if not voice:
        voice = "af_heart"
    voices = tts_manager.valid_kokoro_voices()
    if voice not in voices:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"Invalid voice: {voice}. Valid voices: {voices}"},
        )
    audio_id, audio_path = storage.create_media_filename_with_id(
        media_type="audio", file_extension=".wav"
    )
    tmp_file_id = storage.create_tmp_file(audio_id)

    def bg_task():
        tts_manager.kokoro(
            text=text,
            output_path=audio_path,
            voice=voice,
            speed=speed if speed else 1.0,
        )
        storage.delete_media(tmp_file_id)

    logger.info(f"Adding background task for TTS generation with ID: {audio_id}")
    background_tasks.add_task(bg_task)
    logger.info(f"Background task added for TTS generation with ID: {audio_id}")

    return {"file_id": audio_id}

@v1_media_api_router.get("/audio-tools/tts/chatterbox/languages")
def get_chatterbox_languages():
    return {"languages": chatterbox_supported_languages}

@v1_media_api_router.post("/audio-tools/tts/chatterbox")
def generate_chatterbox_tts(
    background_tasks: BackgroundTasks,
    text: str = Form(..., description="Text to convert to speech"),
    language: Optional[str] = Form(
        "en", description="Language code for multilingual model (default: 'en')"
    ),
    sample_audio_id: Optional[str] = Form(
        None, description="Sample audio ID for voice cloning"
    ),
    sample_audio_file: Optional[UploadFile] = File(
        None, description="Sample audio file for voice cloning"
    ),
    exaggeration: Optional[float] = Form(
        0.5, description="Exaggeration factor for voice cloning, default: 0.5"
    ),
    cfg_weight: Optional[float] = Form(0.5, description="CFG weight for voice cloning, default: 0.5"),
    temperature: Optional[float] = Form(
        0.8, description="Temperature for voice cloning (default: 0.8)"
    ),
    chunk_silence_ms: Optional[int] = Form(
        350, description="Silence duration between chunks in milliseconds (default: 350)"
    ),
    storage: StorageDep = None,
    tts_chatterbox_multi: TTSChatterboxMultilingualDep = None,
    tts_chatterbox: TTSChatterboxDep = None,
):
    """
    Generate audio from text using Chatterbox TTS.
    """
    if language not in chatterbox_supported_languages:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": f"Invalid language: {language}. Supported languages: {list(chatterbox_supported_languages.keys())}"
            },
        )
    
    audio_id, audio_path = storage.create_media_filename_with_id(
        media_type="audio", file_extension=".wav"
    )

    sample_audio_path = None
    if sample_audio_file:
        if not sample_audio_file.filename.endswith(".wav") and not sample_audio_file.filename.endswith(".mp3"):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Sample audio file must be a .wav file."},
            )
        sample_audio_id = storage.upload_media(
            media_type="tmp",
            media_data=sample_audio_file.file.read(),
            file_extension=".wav",
        )
        sample_audio_path = storage.get_media_path(sample_audio_id)
    elif sample_audio_id:
        if not storage.media_exists(sample_audio_id):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": f"Sample audio with ID {sample_audio_id} not found."},
            )
        sample_audio_path = storage.get_media_path(sample_audio_id)

    tmp_file_id = storage.create_tmp_file(audio_id)

    def bg_task():
        try:
            if language == "en":
                tts_chatterbox.chatterbox(
                    text=text,
                    output_path=audio_path,
                    sample_audio_path=sample_audio_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                    temperature=temperature,
                    chunk_silence_ms=chunk_silence_ms,
                )
            else:
                tts_chatterbox_multi.chatterbox(
                    text=text,
                    language=language,
                    output_path=audio_path,
                    sample_audio_path=sample_audio_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                    temperature=temperature,
                    chunk_silence_ms=chunk_silence_ms,
            )
        except Exception as e:
            logger.error(f"Error in Chatterbox TTS: {e}")
        finally:
            storage.delete_media(tmp_file_id)

    # background_tasks.add_task(bg_task)
    logger.info(f"Adding background task for Chatterbox TTS generation with ID: {audio_id}")
    background_tasks.add_task(bg_task)
    logger.info(f"Background task added for Chatterbox TTS generation with ID: {audio_id}")

    return {"file_id": audio_id}

@v1_media_api_router.post('/audio-tools/merge')
def merge_audios(
    background_tasks: BackgroundTasks,
    audio_ids: str = Form(..., description="Comma-separated list of audio IDs to merge"),
    pause: Optional[float] = Form(0.5, description="Pause duration between audios in seconds (default: 0.5)"),
    storage: StorageDep = None,
):
    """
    Merge multiple audio files into one.
    """
    audio_ids = audio_ids.split(",") if audio_ids else []
    if not audio_ids:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "At least one audio ID is required."},
        )

    audio_paths = []
    for audio_id in audio_ids:
        if not storage.media_exists(audio_id):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": f"Audio with ID {audio_id} not found."},
            )
        audio_paths.append(storage.get_media_path(audio_id))

    merged_audio_id, merged_audio_path = storage.create_media_filename_with_id(
        media_type="audio", file_extension=".wav"
    )

    tmp_file_id = storage.create_tmp_file(merged_audio_id)
    tmp_files = [tmp_file_id]
    def bg_task():
        utils = MediaUtils()
        
        def merge_batch(batch_paths):
            """Merge a batch of audio files and return the output path."""
            if len(batch_paths) == 1:
                return batch_paths[0]
            
            batch_id, batch_path = storage.create_media_filename_with_id(
                media_type="tmp", file_extension=".wav"
            )
            tmp_files.append(batch_id)
            
            success = utils.merge_audio_files(
                audio_paths=batch_paths,
                output_path=batch_path,
                pause=pause,
            )
            
            if not success:
                raise Exception(f"Failed to merge batch of {len(batch_paths)} audio files")
            
            return batch_path
        
        try:
            final_result = batch_operation(
                items=audio_paths,
                batch_size=recursive_merge_max_files,
                operation=merge_batch
            )
            
            shutil.move(final_result, merged_audio_path)
                
        except Exception as e:
            logger.error(f"Error during batched audio merge: {e}")
            raise
        finally:
            for tmp_file_id in tmp_files:
                if storage.media_exists(tmp_file_id):
                    storage.delete_media(tmp_file_id)
    
    background_tasks.add_task(bg_task)

    return {"file_id": merged_audio_id}

@v1_media_api_router.post("/storage")
def upload_file(
    file: Optional[UploadFile] = File(None, description="File to upload"),
    url: Optional[str] = Form(None, description="URL of the file to upload (optional)"),
    media_type: Literal["image", "video", "audio", "tmp"] = Form(
        ..., description="Type of media being uploaded"
    ),
    storage: StorageDep = None,
):
    """
    Upload a file and return its ID.
    """
    if media_type not in ["image", "video", "audio", "tmp"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"Invalid media type: {media_type}"},
        )
    if file:
        file_id = storage.upload_media(
            media_type=media_type,
            media_data=file.file.read(),
            file_extension=os.path.splitext(file.filename)[1],
        )

        return {"file_id": file_id}
    elif url:
        if not storage.is_valid_url(url):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": f"Invalid URL: {url}"},
            )
        file_id = storage.upload_media_from_url(media_type=media_type, url=url)
        return {"file_id": file_id}


@v1_media_api_router.get("/storage/{file_id}")
def download_file(file_id: str, storage: StorageDep = None):
    """
    Download a file by its ID.
    """
    if not storage.media_exists(file_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"File with ID {file_id} not found."},
        )

    file_path = storage.get_media_path(file_id)
    return StreamingResponse(
        iterfile(file_path),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={os.path.basename(file_path)}"
        },
    )


@v1_media_api_router.delete("/storage/{file_id}")
def delete_file(file_id: str, storage: StorageDep = None):
    """
    Delete a file by its
    """
    if storage.media_exists(file_id):
        storage.delete_media(file_id)
    return {"status": "success"}


@v1_media_api_router.get("/storage/{file_id}/status")
def file_status(file_id: str, storage: StorageDep = None):
    """
    Check the status of a file by its ID.
    """
    tmp_id = storage.create_tmp_file_id(file_id)
    if storage.media_exists(tmp_id):
        # read the file content to see if there's a progress in it
        tmp_file_path = storage.get_media_path(tmp_id)
        percentage = "n/a"
        with open(tmp_file_path, "r") as f:
            content = f.read().strip()
            percentage = content
        
        return {"status": "processing", "progress": percentage}
    elif storage.media_exists(file_id):
        return {"status": "ready"}
    return {"status": "not_found"}


@v1_media_api_router.post("/video-tools/merge")
def merge_videos(
    background_tasks: BackgroundTasks,
    video_ids: str = Form(..., description=f"List of video IDs to merge - {merge_file_limit} max"),
    background_music_id: Optional[str] = Form(
        None, description="Background music ID (optional)"
    ),
    background_music_volume: Optional[float] = Form(
        0.5, description="Volume for background music (0.0 to 1.0)"
    ),
    storage: StorageDep = None,
):
    """
    Merge multiple videos into one.
    """
    video_ids = video_ids.split(",") if video_ids else []
    if not video_ids:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "At least one video ID is required."},
        )

    if len(video_ids) > merge_file_limit:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"A maximum of {merge_file_limit} video IDs can be merged at once."},
        )

    merged_video_id, merged_video_path = storage.create_media_filename_with_id(
        media_type="video", file_extension=".mp4"
    )

    video_paths = []
    for video_id in video_ids:
        if not storage.media_exists(video_id):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": f"Video with ID {video_id} not found."},
            )
        video_paths.append(storage.get_media_path(video_id))

    if background_music_id and not storage.media_exists(background_music_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": f"Background music with ID {background_music_id} not found."
            },
        )
    background_music_path = (
        storage.get_media_path(background_music_id) if background_music_id else None
    )

    utils = MediaUtils()

    temp_file_id = storage.create_tmp_file(merged_video_id)
    temp_files = [temp_file_id]

    def wait_for_file_ready(file_path, timeout_seconds=30):
        """Wait for file to be completely written and readable"""
        import time
        import os
        
        start_time = time.time()
        last_size = 0
        stable_count = 0
        
        while time.time() - start_time < timeout_seconds:
            if not os.path.exists(file_path):
                time.sleep(0.1)
                continue
                
            try:
                # Check if file size is stable for at least 0.5 seconds
                current_size = os.path.getsize(file_path)
                if current_size == last_size and current_size > 0:
                    stable_count += 1
                    if stable_count >= 5:  # 0.5 seconds of stability
                        # Force OS to flush buffers
                        try:
                            with open(file_path, 'rb') as f:
                                f.read(1024)  # Try to read first chunk
                                os.fsync(f.fileno())  # Force flush
                        except:
                            pass
                        
                        # Final validation - try to get video info
                        video_info = utils.get_video_info(file_path)
                        if video_info and video_info.get("duration", 0) > 0:
                            logger.debug(f"File ready: {file_path}")
                            return True
                        else:
                            logger.warning(f"File exists but invalid: {file_path}")
                            stable_count = 0
                else:
                    stable_count = 0
                    last_size = current_size
                    
            except Exception as e:
                logger.debug(f"File not ready yet: {e}")
                stable_count = 0
                
            time.sleep(0.1)
        
        logger.error(f"File did not become ready within timeout: {file_path}")
        return False

    def bg_task():
        def operation(batch_paths):
            if len(batch_paths) == 1:
                return batch_paths[0]
            
            batch_id, batch_path = storage.create_media_filename_with_id(
                media_type="tmp", file_extension=".mp4"
            )
            temp_files.append(batch_id)
            
            # Use simple concat for same-dimension videos
            success = utils.concat_videos_simple(
                video_paths=batch_paths,
                output_path=batch_path,
            )
            
            if not success:
                storage.delete_media(temp_file_id)
                raise Exception(f"Failed to concatenate batch of {len(batch_paths)} video files")
            
            # CRITICAL: Wait for file to be completely written
            if not wait_for_file_ready(batch_path):
                storage.delete_media(temp_file_id)
                raise Exception(f"Batch output file not ready after timeout: {batch_path}")
            
            return batch_path

        try:
            intermediate_path = batch_operation(
                items=video_paths,
                batch_size=min(20, len(video_paths)),
                operation=operation
            )
            temp_files.append(intermediate_path)

            # Wait for final intermediate file to be ready before proceeding
            if not wait_for_file_ready(intermediate_path):
                raise Exception(f"Intermediate file not ready: {intermediate_path}")

            if background_music_path:
                utils.add_background_music(
                    video_path=intermediate_path,
                    music_path=background_music_path,
                    output_path=merged_video_path,
                    music_volume=background_music_volume,
                )
            else:
                shutil.move(intermediate_path, merged_video_path)

        except Exception as e:
            logger.error(f"Error in video merge background task: {e}")
            raise
        finally:
            for tmp_file_id in temp_files:
                if storage.media_exists(tmp_file_id):
                    storage.delete_media(tmp_file_id)

    background_tasks.add_task(bg_task)
    return {"file_id": merged_video_id}

@v1_media_api_router.get('/fonts')
def list_fonts():
    fonts = set()
    for fname in fm.findSystemFonts(fontpaths=None, fontext='ttf'):
        try:
            prop = fm.FontProperties(fname=fname)
            name = prop.get_name()
            fonts.add(name)
        except RuntimeError:
            continue
    return {"fonts": sorted(fonts)}

@v1_media_api_router.post("/video-tools/generate/tts-captioned-video")
def generate_captioned_video(
    background_tasks: BackgroundTasks,
    background_id: str = Form(..., description="Background image ID"),
    text: Optional[str] = Form(None, description="Text to generate video from, or to use it as alignment with the provided audio_id"),
    width: Optional[int] = Form(1080, description="Width of the video (default: 1080)"),
    height: Optional[int] = Form(
        1920, description="Height of the video (default: 1920)"
    ),
    audio_id: Optional[str] = Form(
        None, description="Audio ID for the video (optional)"
    ),
    kokoro_voice: Optional[str] = Form(
        "af_heart", description="Voice for kokoro TTS (default: af_heart)"
    ),
    kokoro_speed: Optional[float] = Form(
        1.0, description="Speed for kokoro TTS (default: 1.0)"
    ),
    language: Optional[str] = Form(
        None, description="Language code for STT (optional, e.g. 'en', 'fr', 'de'), defaults to None (auto-detect language if audio_id is provided)"
    ),
    alignment_language_code: Optional[str] = Form(
        None, description="ISO-639-3 language code for TTS alignment (optional, e.g. 'eng', 'fra', 'deu'), defaults to None"
    ),
    
    image_effect: Optional[str] = Form("ken_burns", description="Effect to apply to the background image, options: ken_burns, pan, still (default: 'ken_burns')"),

    caption_on: Optional[bool] = Form(True, description="Whether to enable captions (default: True)"),
    
    # Flattened subtitle configuration options
    caption_config_line_count: Optional[int] = Form(1, description="Number of lines per subtitle segment (default: 1)", ge=1, le=5),
    caption_config_line_max_length: Optional[int] = Form(1, description="Maximum characters per line (default: 1)", ge=1, le=200),
    caption_config_font_size: Optional[int] = Form(120, description="Font size for subtitles (default: 50)", ge=8, le=200),
    caption_config_font_name: Optional[str] = Form("Arial", description="Font family name (default: 'EB Garamond', see the available fonts form the /fonts endpoint)"),
    caption_config_font_bold: Optional[bool] = Form(True, description="Whether to use bold font (default: True)"),
    caption_config_font_italic: Optional[bool] = Form(False, description="Whether to use italic font (default: false)"),
    caption_config_font_color: Optional[str] = Form("#fff", description="Font color in hex format (default: '#fff')"),
    caption_config_subtitle_position: Optional[Literal["top", "center", "bottom"]] = Form("top", description="Vertical position of subtitles (default: 'top')"),
    caption_config_shadow_color: Optional[str] = Form("#000", description="Shadow color in hex format (default: '#000')"),
    caption_config_shadow_transparency: Optional[float] = Form(0.4, description="Shadow transparency from 0.0 to 1.0 (default: 0.4)", ge=0.0, le=1.0),
    caption_config_shadow_blur: Optional[int] = Form(10, description="Shadow blur radius (default: 10)", ge=0, le=20),
    caption_config_stroke_color: Optional[str] = Form(None, description="Stroke/outline color in hex format (default: '#000')"),
    caption_config_stroke_size: Optional[int] = Form(5, description="Stroke/outline size (default: 5)", ge=0, le=10),
    
    storage: StorageDep = None,
    tts_manager: TTSManagerDep = None,
    stt: STTDep = None,
):
    """
    Generate a captioned video from text and background image.

    """
    # Build subtitle options from individual parameters
    parsed_subtitle_options = {}
    
    # Only include non-None values
    if caption_config_line_count is not None:
        parsed_subtitle_options['lines'] = caption_config_line_count
    if caption_config_line_max_length is not None:
        parsed_subtitle_options['max_length'] = caption_config_line_max_length
    if caption_config_font_size is not None:
        parsed_subtitle_options['font_size'] = caption_config_font_size
    if caption_config_font_name is not None:
        parsed_subtitle_options['font_name'] = caption_config_font_name
    if caption_config_font_bold is not None:
        parsed_subtitle_options['font_bold'] = caption_config_font_bold
    if caption_config_font_italic is not None:
        parsed_subtitle_options['font_italic'] = caption_config_font_italic
    if caption_config_font_color is not None:
        parsed_subtitle_options['font_color'] = caption_config_font_color
    if caption_config_subtitle_position is not None:
        parsed_subtitle_options['subtitle_position'] = caption_config_subtitle_position
    if caption_config_shadow_color is not None:
        parsed_subtitle_options['shadow_color'] = caption_config_shadow_color
    if caption_config_shadow_transparency is not None:
        parsed_subtitle_options['shadow_transparency'] = caption_config_shadow_transparency
    if caption_config_shadow_blur is not None:
        parsed_subtitle_options['shadow_blur'] = caption_config_shadow_blur
    if caption_config_stroke_color is not None:
        parsed_subtitle_options['stroke_color'] = caption_config_stroke_color
    if caption_config_stroke_size is not None:
        parsed_subtitle_options['stroke_size'] = caption_config_stroke_size
    
    if audio_id and not storage.media_exists(audio_id):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"Audio with ID {audio_id} not found."},
        )
    if not audio_id and kokoro_voice not in tts_manager.valid_kokoro_voices():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"Invalid voice: {kokoro_voice}."},
        )
    media_type = storage.get_media_type(background_id)
    if media_type not in ["image", "video"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"Invalid media type: {media_type}"},
        )
    if not storage.media_exists(background_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Background image with ID {background_id} not found."},
        )

    output_id, output_path = storage.create_media_filename_with_id(
        media_type="video", file_extension=".mp4"
    )
    dimensions = (width, height)
    builder = VideoBuilder(
        dimensions=dimensions,
    )
    builder.set_media_utils(MediaUtils())

    tmp_file_id = storage.create_tmp_file(output_id)

    def bg_task(
        tmp_file_id: str = tmp_file_id,
    ):
        tmp_file_ids = [tmp_file_id]

        # set audio, generate captions
        captions = None
        tts_audio_id = audio_id
        from video.tts import LANGUAGE_VOICE_MAP
        lang_config = LANGUAGE_VOICE_MAP.get(kokoro_voice, {})
        international = lang_config.get("international", False)
        
        if tts_audio_id:
            audio_path = storage.get_media_path(tts_audio_id)
            if caption_on:
                if text:
                    alignment = tts_alignment(audio_path, text, lang_code=alignment_language_code)
                    captions = word_timings_to_captions(alignment)
                else:
                    captions = stt.transcribe(audio_path=audio_path, language=language)[0]
            builder.set_audio(audio_path)
        else:
            tts_audio_id, audio_path = storage.create_media_filename_with_id(
                media_type="audio", file_extension=".wav"
            )
            tmp_file_ids.append(tts_audio_id)
            captions = tts_manager.kokoro(
                text=text,
                output_path=audio_path,
                voice=kokoro_voice,
                speed=kokoro_speed,
            )[0]
            if international and caption_on:
                iso_639_3 = alignment_language_code
                if not iso_639_3:
                    iso_639_3 = iso639.Language.from_part1(lang_config.get("iso639_1", "en")).part3
                alignment = tts_alignment(audio_path, text, lang_code=iso_639_3)
                captions = word_timings_to_captions(alignment)
            
            builder.set_audio(audio_path)

        # create subtitle
        if caption_on:
            captionsManager = Caption()
            subtitle_id, subtitle_path = storage.create_media_filename_with_id(
                media_type="tmp", file_extension=".ass"
            )
            tmp_file_ids.append(subtitle_id)
            
            # create segments based on language
            if international:
                segments = captionsManager.create_subtitle_segments_international(
                    captions=captions,
                    lines=parsed_subtitle_options.get('lines', parsed_subtitle_options.get('lines', 1)),
                    max_length=parsed_subtitle_options.get('max_length', parsed_subtitle_options.get('max_length', 1)),
                )
                logger.bind(
                    segments=segments,
                    captions=captions,
                ).debug("Created international subtitle segments")
            else:
                segments = captionsManager.create_subtitle_segments_english(
                    captions=captions,
                    lines=parsed_subtitle_options.get('lines', parsed_subtitle_options.get("lines", 1)),
                    max_length=parsed_subtitle_options.get('max_length', parsed_subtitle_options.get("max_length", 1)),
                )
            
            captionsManager.create_subtitle(
                segments=segments,
                output_path=subtitle_path,
                dimensions=dimensions,

                font_size=parsed_subtitle_options.get('font_size', 120),
                shadow_blur=parsed_subtitle_options.get('shadow_blur', 10),
                stroke_size=parsed_subtitle_options.get('stroke_size', 5),
                shadow_color=parsed_subtitle_options.get('shadow_color', "#000"),
                stroke_color=parsed_subtitle_options.get('stroke_color', "#000"),
                font_name=parsed_subtitle_options.get('font_name', "Arial"),
                font_bold=parsed_subtitle_options.get('font_bold', True),
                font_italic=parsed_subtitle_options.get('font_italic', False),
                subtitle_position=parsed_subtitle_options.get('subtitle_position', "top"),
                font_color=parsed_subtitle_options.get('font_color', "#fff"),
                shadow_transparency=parsed_subtitle_options.get('shadow_transparency', 0.4),
            )
            builder.set_captions(
                file_path=subtitle_path,
            )

        # resize background image if needed
        background_path = storage.get_media_path(background_id)
        media_type = storage.get_media_type(background_id)
        utils = MediaUtils()
        info = utils.get_video_info(background_path)
        
        if media_type == "image":
            if info.get("width", 0) != width or info.get("height", 0) != height:
                logger.bind(
                    image_width=info.get("width", 0),
                    image_height=info.get("height", 0),
                    target_width=width,
                    target_height=height,
                ).debug(
                    "Resizing background image to fit video dimensions"
                )
                _, resized_background_path = storage.create_media_filename_with_id(
                    media_type="image", file_extension=".jpg"
                )   
                resize_image_cover(
                    image_path=background_path,
                    output_path=resized_background_path,
                    target_width=width,
                    target_height=height,
                )
                background_path = resized_background_path

            builder.set_background_image(
                background_path,
                effect_config={
                    "effect": image_effect,
                }
            )
        elif media_type == "video":
            builder.set_background_video(
                background_path,
            )

        builder.set_output_path(output_path)

        builder.execute()

        for tmp_file_id in tmp_file_ids:
            if storage.media_exists(tmp_file_id):
                storage.delete_media(tmp_file_id)

    logger.info(f"Adding background task for captioned video generation with ID: {output_id}")
    background_tasks.add_task(bg_task, tmp_file_id=tmp_file_id)
    logger.info(f"Background task added for captioned video generation with ID: {output_id}")

    return {
        "file_id": output_id,
    }

# https://ffmpeg.org/ffmpeg-filters.html#colorkey
@v1_media_api_router.post("/video-tools/add-colorkey-overlay")
def add_colorkey_overlay(
    background_tasks: BackgroundTasks,
    video_id: str = Form(..., description="Video ID to overlay"),
    overlay_video_id: str = Form(..., description="Overlay image ID"),
    color: Optional[str] =  Form(
        "green", description="Set the color for which alpha will be set to 0 (full transparency). Use name of the color or hex code (e.g. 'red' or '#ff0000')"
    ),
    similarity: Optional[float] = Form(
        0.1, description="Set the radius from the key color within which other colors also have full transparency (Default: 0.1)"
    ),
    blend: Optional[float] = Form(
        0.1, description="Set how the alpha value for pixels that fall outside the similarity radius is computed (default: 0.1)"
    ),
    storage: StorageDep = None,
):
    """
    Overlay a video on a video with the specified colorkey and intensity
    """
    
    if not storage.media_exists(video_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Video with ID {video_id} not found."},
        )
    if not storage.media_exists(overlay_video_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Overlay video with ID {overlay_video_id} not found."},
        )
    
    video_path = storage.get_media_path(video_id)
    overlay_video_path = storage.get_media_path(overlay_video_id)
    
    output_id, output_path = storage.create_media_filename_with_id(
        media_type="video", file_extension=".mp4"
    )
    
    tmp_file_id = storage.create_tmp_file(output_id)
    
    def bg_task():
        utils = MediaUtils()
        utils.colorkey_overlay(
            input_video_path=video_path,
            overlay_video_path=overlay_video_path,
            output_video_path=output_path,
            color=color,
            similarity=similarity,
            blend=blend,
        )
        storage.delete_media(tmp_file_id)
    
    logger.info(f"Adding background task for colorkey overlay with ID: {output_id}")
    background_tasks.add_task(bg_task)
    logger.info(f"Background task added for colorkey overlay with ID: {output_id}")
    
    return {
        "file_id": output_id,
    }

@v1_media_api_router.post("/video-tools/add-overlay")
def add_overlay(
    background_tasks: BackgroundTasks,
    video_id: str = Form(..., description="Video ID to overlay"),
    overlay_id: str = Form(..., description="Overlay image or video ID"),
    opacity: Optional[float] = Form(
        0.4, description="Opacity of the overlay image (0.0 to 1.0, default: 0.4)"
    ),
    storage: StorageDep = None,
):
    """
    Add an image or video overlay to a video with specified opacity.
    """
    
    # Check if the input video exists
    if not storage.media_exists(video_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Video with ID {video_id} not found."},
        )
    
    # Check if the overlay exists
    if not storage.media_exists(overlay_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Overlay with ID {overlay_id} not found."},
        )
    
    # Validate opacity parameter
    if opacity is not None and (opacity < 0.0 or opacity > 1.0):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Opacity must be between 0.0 and 1.0."},
        )
    
    # Get the overlay type (image or video)
    overlay_type = storage.get_media_type(overlay_id)
    if overlay_type not in ["image", "video"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"Invalid overlay type: {overlay_type}. Must be image or video."},
        )
    
    # Get file paths
    video_path = storage.get_media_path(video_id)
    overlay_path = storage.get_media_path(overlay_id)
    
    # Get video duration for the overlay process
    utils = MediaUtils()
    video_info = utils.get_video_info(video_path)
    video_duration = video_info.get("duration", 0)
    
    if not video_duration:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Failed to get video duration from input video."},
        )
    
    # Create output path and tmp file ID
    output_id, output_path = storage.create_media_filename_with_id(
        media_type="video", file_extension=".mp4"
    )
    
    tmp_file_id = storage.create_tmp_file(output_id)
    
    def bg_task():
        try:
            utils = MediaUtils()
            success = utils.overlay(
                type=overlay_type,
                input_video_path=video_path,
                overlay_path=overlay_path,
                video_duration=video_duration,
                output_video_path=output_path,
                opacity=opacity if opacity is not None else 0.4,
            )
            
            if not success:
                logger.error(f"Failed to add {overlay_type} overlay to video")
        except Exception as e:
            logger.bind(error=str(e)).error(f"Error adding {overlay_type} overlay to video")
        finally:
            # Clean up tmp file
            if storage.media_exists(tmp_file_id):
                storage.delete_media(tmp_file_id)
    
    logger.info(f"Adding background task for {overlay_type} overlay with ID: {output_id}")
    background_tasks.add_task(bg_task)
    logger.info(f"Background task added for {overlay_type} overlay with ID: {output_id}")
    
    return {
        "file_id": output_id,
    }
    

@v1_media_api_router.get("/video-tools/extract-frame/{video_id}")
def extract_frame(
    video_id: str,
    timestamp: Optional[float] = Query(1.0, description="Timestamp in seconds to extract frame from (default: 1.0)"),
    storage: StorageDep = None,
):
    """
    Extract a frame from a video at a specified timestamp.
    
    Args:
        video_id: Video ID to extract frame from
        timestamp: Optional timestamp in seconds to extract frame from (default: first frame)
    """
    if not storage.media_exists(video_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Video with ID {video_id} not found."},
        )
    
    video_path = storage.get_media_path(video_id)
    
    _, output_path = storage.create_media_filename_with_id(
        media_type="image", file_extension=".jpg"
    )
    
    utils = MediaUtils()
    video_info = utils.get_video_info(video_path)
    if video_info.get("duration", 0) <= float(timestamp):
        timestamp = video_info.get("duration", 0) - 0.3

    success = utils.extract_frame(
        video_path=video_path,
        output_path=output_path,
        time_seconds=timestamp,
    )
    
    if not success:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to extract frame from video."},
        )
    
    # Load file into memory
    with open(output_path, "rb") as file:
        file_data = file.read()
    
    # Remove the output file
    os.remove(output_path)
    
    # Create streaming response with appropriate headers
    from io import BytesIO
    return StreamingResponse(
        BytesIO(file_data),
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f"attachment; filename=frame_{video_id}_{timestamp or 'first'}.jpg"
        },
    )
    
# extract x number of frames from the video, equally spaced
@v1_media_api_router.post('/video-tools/extract-frames')
def extract_frame_from_url(
    url: str = Form(..., description="URL of the video to extract frame from"),
    amount: int = Form(5, description="Number of frames to extract from the video (default: 5)"),
    length_seconds: Optional[float] = Form(None, description="Length of the video in seconds (optional)"),
    stitch: Optional[bool] = Form(False, description="Whether to stitch the frames into a single image (default: False)"),
    storage: StorageDep = None,
):
    template_id, template_path = storage.create_media_template(
        media_type="image", file_extension=".jpg"
    )
    utils = MediaUtils()
    
    if not length_seconds:
        video_info = utils.get_video_info(url)
        length_seconds = video_info.get("duration", 0)
    
    utils.extract_frames(
        video_path=url,
        length_seconds=length_seconds,
        amount=amount,
        output_template=template_path,
    )
    
    image_ids = []
    for i in range(amount):
        padded_index = str(i + 1).zfill(2)
        
        image_id = template_id.replace("%02d", padded_index)
        image_ids.append(f"image_{image_id}") # the image_id needs to be prefixed with "image_"

    if stitch:
        # Load extracted frame images
        images = []
        logger.bind(image_ids=image_ids).debug("Loading extracted frame images for stitching")
        for image_id in image_ids:
            if storage.media_exists(image_id):
                image_path = storage.get_media_path(image_id)
                img = Image.open(image_path)
                images.append(img)
        
        if not images:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "No valid frame images found for stitching."}
            )
        
        # Import and use the refactored stitch_images function
        from utils.image import stitch_images
        try:
            stitched_image = stitch_images(images, max_width=1920, max_height=1080)
            
            # Convert PIL image to JPEG format in memory
            img_buffer = BytesIO()
            stitched_image.save(img_buffer, format='JPEG', quality=95)
            img_buffer.seek(0)
            
            # Clean up individual frame files
            for image_id in image_ids:
                if storage.media_exists(image_id):
                    storage.delete_media(image_id)
            
            return StreamingResponse(
                img_buffer,
                media_type="image/jpeg",
                headers={
                    "Content-Disposition": f"attachment; filename=stitched_frames.jpg"
                },
            )
        except Exception as e:
            logger.error(f"Error stitching frame images: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Failed to stitch frame images."}
            )
    
    return {
        "message": f"Extracted {amount} frames from the video at {url}. The frames are saved in the template directory.",
        "template_id": template_id,
        "template_path": template_path,
        "image_ids": image_ids,
    }


@v1_media_api_router.get("/video-tools/info/{file_id}")
def get_video_info(
    file_id: str,
    storage: StorageDep = None,
):
    """
    Get information about a video file.
    """
    if not storage.media_exists(file_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Video with ID {file_id} not found."},
        )
    
    video_path = storage.get_media_path(file_id)
    
    utils = MediaUtils()
    info = utils.get_video_info(video_path)
    
    return info

@v1_media_api_router.get("/audio-tools/info/{file_id}")
def get_audio_info(
    file_id: str,
    storage: StorageDep = None,
):
    """
    Get information about an audio file.
    """
    if not storage.media_exists(file_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Audio with ID {file_id} not found."},
        )
    
    audio_path = storage.get_media_path(file_id)
    
    utils = MediaUtils()
    info = utils.get_audio_info(audio_path)
    
    return info

@v1_media_api_router.post("/video-tools/long-form-ambient")
def generate_long_form_ambient_video(
    background_tasks: BackgroundTasks,
    video_id: str = Form(..., description="Video ID to generate ambient video from"),
    audio_id: Optional[str] = Form(None, description="(duplicate) Music ID for the video background music (optional)"),
    music_id: Optional[str] = Form(None, description="Music ID to use for the video background music (optional)"),
    dialogue_ids: Optional[str] = Form(None, description="Comma-separated list of dialogue audio IDs to overlay on the ambient video (optional)"),
    dialogue_pause_seconds: Optional[float] = Form(0.5, description="Pause in seconds between dialogue clips (default: 0.5)"),
    music_volume: Optional[float] = Form(1, description="Volume for the music (0.0 to 1.0, default: 1)"),
    duration_minutes: Optional[int] = Form(10, description="Duration of the ambient video in minutes (default: 10), minimum: 10, maximum: 180"),
    width: Optional[int] = Form(1920, description="Width of the video (default: 1920), maximum is 1920"),
    height: Optional[int] = Form(1080, description="Height of the video (default: 1080), maximum is 1080"),
    ambient_sounds: Optional[str] = Form(None, description="Comma-separated list of ambient sounds and their volume in the format: 'TYPE:VOLUME,TYPE:VOLUME', e.g. 'rain:1.0,wind:0.5'."),
    storage: StorageDep = None,
):
    """
    Generate a long-form ambient video
    """
    if duration_minutes < 10 or duration_minutes > 180:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Duration must be between 10 and 180 minutes."},
        )
    
    if not storage.media_exists(video_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Video with ID {video_id} not found."},
        )
        
    if music_volume < 0.0 or music_volume > 1.0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Music volume must be between 0.0 and 1.0."},
        )
    if width > 1920 or height > 1080:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Width cannot be greater than 1920 and height cannot be greater than 1080."},
        )

    # Determine which audio source to use
    music_id = audio_id or music_id  # audio_id is a duplicate of music_id, prefer music_id
    ambient_configs = parse_ambient_config(ambient_sounds)
    
    # Validate that either dialogue_ids, ambient config or music_id is provided
    dialogue_ids_list = [id.strip() for id in dialogue_ids.split(",") if id.strip()] if dialogue_ids else []
    if len(dialogue_ids_list) == 0 and not music_id and len(ambient_configs) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Either dialogue_ids, ambient config or music_id must be provided."},
        )
    
    for dialogue_id in dialogue_ids_list:
        if not storage.media_exists(dialogue_id.strip()):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": f"Dialogue audio with ID {dialogue_id.strip()} not found."},
            )
    
    # Validate music_id exists if provided
    if music_id and not storage.media_exists(music_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Music with ID {music_id} not found."},
        )
        
    output_id, output_path = storage.create_media_filename_with_id(
        media_type="video", file_extension=".mp4"
    )
    
    context_logger = logger.bind(
        video_id=video_id,
        music_id=music_id,
        dialogue_ids=dialogue_ids,
        output_id=output_id,
        duration_minutes=duration_minutes,
        width=width,
        height=height,
        ambient_sounds=ambient_sounds
    )
    
    tmp_file_id = storage.create_tmp_file(output_id)
    tmp_files = [tmp_file_id]

    def bg_task():
        composer = AudioComposer()
        utils = MediaUtils()
        
        if duration_minutes:
            composer.with_duration(duration_minutes * 60.0)
     
        if dialogue_ids_list:
            # merge dialogue audios as base, and set them as base audio for the composer
            context_logger.debug("Merging dialogue audios")
            dialogue_paths = [storage.get_media_path(dialogue_id.strip()) for dialogue_id in dialogue_ids_list]
            
            merged_dialogue_id, merged_dialogue_path = storage.create_media_filename_with_id(
                media_type="audio", file_extension=".wav"
            )
            tmp_files.append(merged_dialogue_id)
            
            utils.merge_audio_files(
                audio_paths=dialogue_paths,
                output_path=merged_dialogue_path,
                pause=dialogue_pause_seconds
            )
            composer.with_dialogue(merged_dialogue_path)

        if music_id:
            # use music as base audio for the composer
            context_logger.debug("Using music as base audio")
            music_path = storage.get_media_path(music_id)
            overlay_config = extract_looping_audio(audio_path=music_path)
            composer.with_overlay_config(overlay_config)
            composer.with_overlay_volume(music_volume)
        if len(ambient_configs) > 0:
            context_logger.debug("Adding ambient sounds")
            composer.with_ambient_configs(ambient_configs)
        
        # composite audio
        final_audio_id, final_audio_path = storage.create_media_filename_with_id(
            media_type="audio", file_extension=".wav"
        )
        tmp_files.append(final_audio_id)
        context_logger.debug("Composing final audio")
        composer.compose(final_audio_path)
        
        
        video_path = storage.get_media_path(video_id)
        
        # Step 5: Create final ambient video
        context_logger.debug("Creating ambient video")
        createAmbientVideo(
            video_path=video_path,
            dimensions=(width, height),
            audio_path=final_audio_path,
            output_path=output_path,
            tmp_file=storage.get_media_path(tmp_file_id)
        )
        
        # Clean up temporary files
        for tmp_file in tmp_files:
            if storage.media_exists(tmp_file):
                storage.delete_media(tmp_file)
        
    
    background_tasks.add_task(bg_task)
    
    return {
        "file_id": output_id
    }

@v1_media_api_router.post("/audio-tools/extend-audio")
def extend_audio(
    background_tasks: BackgroundTasks,
    audio_id: str = Form(..., description="Audio ID to extend"),
    duration_minutes: Optional[int] = Form(10, description="Duration to extend the audio to in minutes, minimum: 10, maximum: 180 (3 hours)"),
    storage: StorageDep = None,
):
    """
    Extend an audio file to a specified duration.
    """
    if not storage.media_exists(audio_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Audio with ID {audio_id} not found."},
        )
    
    if duration_minutes > 180 or duration_minutes < 10:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Duration must be between 10 and 180 minutes."},
        )
    
    audio_path = storage.get_media_path(audio_id)
    
    utils = MediaUtils()
    audio_info = utils.get_audio_info(audio_path)
    audio_duration = audio_info.get("duration", 0)
    
    if audio_duration > duration_minutes * 60:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": f"Audio duration ({audio_duration} seconds) is longer than the requested extension duration ({duration_minutes} minutes)."
            },
        )
    
    output_id, output_path = storage.create_media_filename_with_id(
        media_type="audio", file_extension=".mp3"
    )
    
    tmp_file_id = storage.create_tmp_file(output_id)
    
    def bg_task():
        extendAudio(
            audio_path=audio_path,
            output_path=output_path,
            duration_seconds=duration_minutes * 60.0
        )
        logger.debug(f"Extended audio saved to {output_path}")
        storage.delete_media(tmp_file_id)
    
    background_tasks.add_task(bg_task)
    
    return {
        "file_id": output_id
    }

# todo add language detection with whisper or other solution
@v1_media_api_router.post("/audio-tools/align-script")
def align_script(
    audio_id: str = Form(..., description="Audio ID to align script to"),
    script: str = Form(..., description="Script text to align"),
    mode: Optional[Literal['word', 'sentence', 'sentence_punc', 'fixed_words', 'max_chars']] = Form('sentence', description="Segmentation mode; one of: 'word', 'sentence', 'sentence_punc', 'fixed_words', 'max_chars' (default: 'sentence')"),
    limit: Optional[int] = Form(None, description="Maximum count per chunk. For 'fixed_words': max words. For 'max_chars': max characters. If None, defaults apply."),
    lang_code: Optional[str] = Form(None, description="ISO-639-3 language code for alignment (default: None)"),
    storage: StorageDep = None
):
    """
    Align a script to an audio file and return word timings and segmented chunks.
    """
    if not storage.media_exists(audio_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Audio with ID {audio_id} not found."},
        )
    
    if lang_code is not None and len(lang_code) != 3:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "lang_code must be a valid ISO-639-3 code (3 letters)."},
        )
    
    audio_path = storage.get_media_path(audio_id)
    
    word_timings = tts_alignment(
        speech_file=audio_path,
        text=script,
        lang_code=lang_code
    )
    
    if not word_timings:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Failed to align script to audio."},
        )
    
    segments = segment_from_word_timings(
        word_timings=word_timings,
        mode=mode,
        limit=limit
    )
    
    return segments

# revenge story video generation endpoint

class RevengeStoryVideoRequest(BaseModel):
    """Request model for revenge story video generation"""
    background_video_id: str
    person_image_id: str
    text: str
    character_name: str
    kokoro_voice: str = "af_heart"
    kokoro_speed: float = 1.0
    width: int = 1920
    height: int = 1080
    font_size: int = 100
    max_caption_length: int = 50
    caption_lines: int = 1


@v1_media_api_router.post("/video-tools/revenge-story")
def generate_revenge_story_video_json(
    request: RevengeStoryVideoRequest,
    background_tasks: BackgroundTasks,
    storage: StorageDep = None,
    tts_manager: TTSManagerDep = None,
):
    """
    Generate a revenge story video with TTS audio, captions, and character overlay.
    This endpoint accepts JSON body instead of form data.
    
    This endpoint:
    1. Generates audio using Kokoro TTS
    2. Creates word timings (with alignment for international languages)
    3. Generates subtitles
    4. Creates character overlay image
    5. Generates final revenge video with all components
    """
    # Validate that required media exists
    if not storage.media_exists(request.background_video_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Background video with ID {request.background_video_id} not found."},
        )
    
    if not storage.media_exists(request.person_image_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"Person image with ID {request.person_image_id} not found."},
        )
    
    # Validate TTS voice
    valid_voices = tts_manager.valid_kokoro_voices()
    if request.kokoro_voice not in valid_voices:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"Invalid voice '{request.kokoro_voice}'. Valid voices: {valid_voices}"},
        )

    logger.debug(f"Received revenge story video generation request: {request.json()}")
    
    # Create output file
    output_id, output_path = storage.create_media_filename_with_id(
        media_type="video", file_extension=".mp4"
    )
    
    context_logger = logger.bind(
        background_video_id=request.background_video_id,
        person_image_id=request.person_image_id,
        character_name=request.character_name,
        kokoro_voice=request.kokoro_voice,
        output_id=output_id,
        text_length=len(request.text)
    )
    
    def bg_task():
        tmp_file_id = storage.create_tmp_file(output_id)
        tmp_files = [tmp_file_id]
        try:
            context_logger.info("Starting revenge story video generation")
            
            # Import required modules
            from video.revenge_video import createRevengeStoryVideo
            from video.tts import LANGUAGE_VOICE_MAP
            from utils.image import create_overlay
            
            dimensions = (request.width, request.height)
            
            # Step 1: Generate audio using Kokoro TTS
            context_logger.info("Generating audio with Kokoro TTS")
            audio_id, audio_path = storage.create_media_filename_with_id(
                media_type="audio", file_extension=".wav"
            )
            tmp_files.append(audio_id)
            
            captions, audio_duration = tts_manager.kokoro(
                text=request.text,
                output_path=audio_path,
                voice=request.kokoro_voice,
                speed=request.kokoro_speed,
            )
            
            context_logger.info(f"Audio generated with duration: {audio_duration} seconds")
            
            # Step 2: Determine if we need alignment or can use TTS captions
            lang_config = LANGUAGE_VOICE_MAP.get(request.kokoro_voice, {})
            international = lang_config.get("international", False)
            
            if international:
                context_logger.info("Using TTS alignment for international language")
                # Get ISO-639-3 language code for alignment
                iso_639_3 = lang_config.get("iso639_1", "en")
                if iso_639_3:
                    iso_639_3 = iso639.Language.from_part1(iso_639_3).part3
                else:
                    iso_639_3 = "eng"  # Default to English
                
                # Perform alignment
                word_timings = tts_alignment(audio_path, request.text, lang_code=iso_639_3)
                captions = word_timings_to_captions(word_timings)
                context_logger.info(f"Generated {len(captions)} caption segments from alignment")
            else:
                context_logger.info("Using TTS-generated captions for English")
                context_logger.info(f"Generated {len(captions)} caption segments from TTS")
            
            # Step 3: Create subtitle file
            context_logger.info("Creating subtitle file")
            caption_manager = Caption()
            subtitle_id, subtitle_path = storage.create_media_filename_with_id(
                media_type="tmp", file_extension=".ass"
            )
            tmp_files.append(subtitle_id)
            
            # Create segments based on language
            if international:
                segments = caption_manager.create_subtitle_segments_international(
                    captions=captions,
                    lines=request.caption_lines,
                    max_length=request.max_caption_length,
                )
            else:
                segments = caption_manager.create_subtitle_segments_english(
                    captions=captions,
                    lines=request.caption_lines,
                    max_length=request.max_caption_length,
                )
            
            # Create the subtitle file
            caption_manager.create_subtitle(
                segments=segments,
                output_path=subtitle_path,
                dimensions=dimensions,
                font_size=request.font_size,
                shadow_blur=10,
                stroke_size=3,
                shadow_color="#000",
                stroke_color="#000",
                font_name="Arial",
                font_bold=True,
                font_italic=False,
                subtitle_position="bottom",
                font_color="#fff",
                shadow_transparency=0.4,
                subtitle_postition_from_top=0.65
            )
            
            context_logger.info("Subtitle file created")
            
            # Step 4: Create overlay image
            context_logger.info("Creating character overlay image")
            overlay_id, overlay_path = storage.create_media_filename_with_id(
                media_type="image", file_extension=".png"
            )
            tmp_files.append(overlay_id)
            
            person_image_path = storage.get_media_path(request.person_image_id)
            
            create_overlay(
                person_image_path=person_image_path,
                volume_icon_path="assets/icons/icon_volume.png",
                font_path="assets/fonts/noto.ttf",
                display_name=request.character_name,
                output_path=overlay_path,
            )
            
            context_logger.info("Character overlay image created")
            
            # Step 5: Generate revenge story video
            context_logger.info("Generating final revenge story video")
            background_video_path = storage.get_media_path(request.background_video_id)
            
            from video.config import device
            
            result = createRevengeStoryVideo(
                dimensions=dimensions,
                video_path=background_video_path,
                audio_path=audio_path,
                subtitle_path=subtitle_path,
                overlay_path=overlay_path,
                output_path=output_path,
                cuda=device.type == "cuda",
                tmp_file=storage.get_media_path(tmp_file_id)
            )
            
            if result:
                context_logger.success("Revenge story video generated successfully")
            else:
                context_logger.error("Failed to generate revenge story video")
                return
            
            # Clean up temporary files
            context_logger.info("Cleaning up temporary files")
            for tmp_file_id in tmp_files:
                if storage.media_exists(tmp_file_id):
                    storage.delete_media(tmp_file_id)
            
        except Exception as e:
            context_logger.error(f"Failed to generate revenge story video: {str(e)}")
            # Clean up on error
            for tmp_file_id in tmp_files:
                if storage.media_exists(tmp_file_id):
                    storage.delete_media(tmp_file_id)
            raise
    
    context_logger.info("Adding background task for revenge story video generation")
    background_tasks.add_task(bg_task)
    
    return {
        "file_id": output_id,
        "message": "Revenge story video generation started in background"
    }

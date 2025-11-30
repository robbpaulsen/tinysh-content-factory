"""FFmpeg wrapper for local media processing.

Ported from server-code-and-layout/video/media.py
"""

import json
import subprocess
import time
from pathlib import Path

from loguru import logger


class MediaUtils:
    """Utilities for FFmpeg operations (probing, merging, etc.)"""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """Initialize MediaUtils.

        Args:
            ffmpeg_path: Path to ffmpeg executable (default: "ffmpeg" in PATH)
        """
        self.ffmpeg_path = ffmpeg_path

    def get_audio_info(self, file_path: str | Path) -> dict:
        """Retrieve audio information (duration, codec, bitrate, etc.)

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary with audio information:
            - duration: float (seconds)
            - channels: int
            - sample_rate: str
            - codec: str
            - bitrate: str
        """
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                "-select_streams",
                "a:0",  # First audio stream
                str(file_path),
            ]

            success, stdout, stderr = self.execute_ffprobe_command(cmd, "get audio info")

            if not success:
                raise Exception(f"ffprobe failed: {stderr}")

            probe_data = json.loads(stdout)
            format_info = probe_data.get("format", {})
            streams = probe_data.get("streams", [])

            if not streams:
                raise Exception("No audio stream found in file")

            audio_stream = streams[0]

            audio_info = {
                "duration": float(format_info.get("duration", 0)),
                "channels": audio_stream.get("channels", 0),
                "sample_rate": audio_stream.get("sample_rate", "0"),
                "codec": audio_stream.get("codec_name", ""),
                "bitrate": audio_stream.get("bit_rate", "0"),
            }

            return audio_info

        except Exception as e:
            logger.bind(file_path=str(file_path), error=str(e)).error(
                "Error getting audio info"
            )
            return {}

    def get_video_info(self, file_path: str | Path) -> dict:
        """Retrieve video information (duration, dimensions, codec, fps, etc.)

        Args:
            file_path: Path to video file

        Returns:
            Dictionary with video information:
            - duration: float (seconds)
            - width: int
            - height: int
            - fps: str
            - aspect_ratio: str
            - codec: str
        """
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                "-select_streams",
                "v:0",  # First video stream
                str(file_path),
            ]

            success, stdout, stderr = self.execute_ffprobe_command(cmd, "get video info")

            if not success:
                raise Exception(f"ffprobe failed: {stderr}")

            probe_data = json.loads(stdout)
            format_info = probe_data.get("format", {})
            streams = probe_data.get("streams", [])

            if not streams:
                raise Exception("No video stream found in file")

            video_stream = streams[0]

            video_info = {
                "duration": float(format_info.get("duration", 0)),
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "fps": video_stream.get("avg_frame_rate", "0/1").split("/")[0],
                "aspect_ratio": video_stream.get("display_aspect_ratio", "1:1"),
                "codec": video_stream.get("codec_name"),
            }

            return video_info

        except Exception as e:
            logger.bind(file_path=str(file_path), error=str(e)).error(
                "Error getting video info"
            )
            return {}

    def merge_videos(
        self,
        video_paths: list[str | Path],
        output_path: str | Path,
        background_music_path: str | Path = None,
        background_music_volume: float = 0.5,
    ) -> bool:
        """Merge multiple videos into one, optionally with background music.

        Args:
            video_paths: List of video file paths to merge
            output_path: Output path for merged video
            background_music_path: Optional background music file
            background_music_volume: Music volume (0.0-1.0, default 0.5)

        Returns:
            bool: True if successful, False otherwise
        """
        if not video_paths:
            logger.error("No video paths provided for merging")
            return False

        start = time.time()
        context_logger = logger.bind(
            number_of_videos=len(video_paths),
            output_path=str(output_path),
            background_music=bool(background_music_path),
            background_music_volume=background_music_volume,
        )

        try:
            # Get dimensions from first video
            first_video_info = self.get_video_info(video_paths[0])
            if not first_video_info:
                context_logger.error("Failed to get video info from first video")
                return False

            target_width = first_video_info.get("width", 1080)
            target_height = first_video_info.get("height", 1920)
            target_dimensions = f"{target_width}:{target_height}"

            context_logger.bind(
                target_width=target_width, target_height=target_height
            ).debug("Using dimensions from first video")

            # Base command
            cmd = [self.ffmpeg_path, "-y"]

            # Add input video files
            for video_path in video_paths:
                cmd.extend(["-i", str(video_path)])

            # Add background music if provided
            music_input_index = None
            if background_music_path:
                cmd.extend(["-stream_loop", "-1", "-i", str(background_music_path)])
                music_input_index = len(video_paths)

            # Build filter_complex for concatenation
            if len(video_paths) == 1:
                # Single video
                audio_info = self.get_audio_info(video_paths[0])
                has_audio = bool(audio_info.get("duration", 0) > 0)

                if background_music_path:
                    if has_audio:
                        cmd.extend(
                            [
                                "-filter_complex",
                                f"[0:v]scale={target_dimensions}:force_original_aspect_ratio=decrease,pad={target_dimensions}:(ow-iw)/2:(oh-ih)/2:black,fps=30[v];[{music_input_index}:a]volume={background_music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first[a]",
                                "-map",
                                "[v]",
                                "-map",
                                "[a]",
                            ]
                        )
                    else:
                        cmd.extend(
                            [
                                "-filter_complex",
                                f"[0:v]scale={target_dimensions}:force_original_aspect_ratio=decrease,pad={target_dimensions}:(ow-iw)/2:(oh-ih)/2:black,fps=30[v];[{music_input_index}:a]volume={background_music_volume}[a]",
                                "-map",
                                "[v]",
                                "-map",
                                "[a]",
                            ]
                        )
                else:
                    if has_audio:
                        cmd.extend(
                            [
                                "-filter_complex",
                                f"[0:v]scale={target_dimensions}:force_original_aspect_ratio=decrease,pad={target_dimensions}:(ow-iw)/2:(oh-ih)/2:black,fps=30[v]",
                                "-map",
                                "[v]",
                                "-map",
                                "0:a",
                            ]
                        )
                    else:
                        # No audio, create silent audio
                        video_info = self.get_video_info(video_paths[0])
                        video_duration = video_info.get("duration", 10)
                        cmd.extend(
                            [
                                "-filter_complex",
                                f"[0:v]scale={target_dimensions}:force_original_aspect_ratio=decrease,pad={target_dimensions}:(ow-iw)/2:(oh-ih)/2:black,fps=30[v];anullsrc=channel_layout=stereo:sample_rate=48000:duration={video_duration}[a]",
                                "-map",
                                "[v]",
                                "-map",
                                "[a]",
                            ]
                        )
            else:
                # Multiple videos - normalize and concatenate
                videos_with_audio = []
                for i, video_path in enumerate(video_paths):
                    audio_info = self.get_audio_info(video_path)
                    has_audio = bool(audio_info.get("duration", 0) > 0)
                    videos_with_audio.append(has_audio)
                    context_logger.bind(video_index=i, has_audio=has_audio).debug(
                        "Checked audio stream"
                    )

                # Normalize video streams
                normalize_filters = []
                for i in range(len(video_paths)):
                    normalize_filters.append(
                        f"[{i}:v]scale={target_dimensions}:force_original_aspect_ratio=decrease,pad={target_dimensions}:(ow-iw)/2:(oh-ih)/2:black,fps=30,format=yuv420p[v{i}n]"
                    )

                # Create audio streams (silent for videos without audio)
                audio_filters = []
                for i in range(len(video_paths)):
                    if not videos_with_audio[i]:
                        video_info = self.get_video_info(video_paths[i])
                        video_duration = video_info.get("duration", 10)
                        audio_filters.append(
                            f"anullsrc=channel_layout=stereo:sample_rate=48000:duration={video_duration}[a{i}n]"
                        )
                    else:
                        audio_filters.append(
                            f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo[a{i}n]"
                        )

                # Concat filter
                concat_inputs = "".join([f"[v{i}n][a{i}n]" for i in range(len(video_paths))])
                all_filters = normalize_filters + audio_filters
                filter_complex = (
                    ";".join(all_filters)
                    + f";{concat_inputs}concat=n={len(video_paths)}:v=1:a=1[v][a]"
                )

                if background_music_path:
                    filter_complex += f";[{music_input_index}:a]volume={background_music_volume}[bg];[a][bg]amix=inputs=2:duration=first[final_a]"
                    cmd.extend(
                        [
                            "-filter_complex",
                            filter_complex,
                            "-map",
                            "[v]",
                            "-map",
                            "[final_a]",
                        ]
                    )
                else:
                    cmd.extend(
                        ["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]"]
                    )

            # Video codec settings (CPU fallback - will add NVENC detection later)
            cmd.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"])

            # Audio codec settings
            cmd.extend(["-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", str(output_path)])

            # Calculate expected duration
            expected_duration = sum(
                self.get_video_info(vp).get("duration", 0) for vp in video_paths
            )

            success = self.execute_ffmpeg_command(
                cmd,
                "merge videos",
                expected_duration=expected_duration,
                show_progress=True,
            )

            if success:
                context_logger.bind(execution_time=time.time() - start).debug(
                    "Videos merged successfully"
                )
                return True
            else:
                context_logger.error("FFmpeg failed to merge videos")
                return False

        except Exception as e:
            context_logger.bind(error=str(e)).error("Error merging videos")
            return False

    def format_time(self, seconds: float) -> str:
        """Format seconds into HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def execute_ffmpeg_command(
        self,
        cmd: list,
        operation_name: str,
        expected_duration: float = None,
        show_progress: bool = True,
    ) -> bool:
        """Execute FFmpeg command with logging and progress tracking.

        Args:
            cmd: FFmpeg command as list
            operation_name: Operation name for logging
            expected_duration: Expected duration for progress calculation
            show_progress: Whether to show progress

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.bind(command=" ".join(cmd), operation=operation_name).debug(
                f"Executing FFmpeg command for {operation_name}"
            )

            process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                text=True,
            )

            # Process output line by line
            for line in process.stderr:
                # Extract time for progress tracking
                if (
                    show_progress
                    and expected_duration
                    and "time=" in line
                    and "speed=" in line
                ):
                    try:
                        time_str = line.split("time=")[1].split(" ")[0]
                        h, m, s = time_str.split(":")
                        seconds = float(h) * 3600 + float(m) * 60 + float(s)
                        progress = min(100, (seconds / expected_duration) * 100)
                        logger.info(
                            f"{operation_name}: {progress:.2f}% complete (Time: {time_str} / Total: {self.format_time(expected_duration)})"
                        )
                    except (ValueError, IndexError):
                        pass
                elif any(
                    keyword in line
                    for keyword in [
                        "ffmpeg version",
                        "built with",
                        "configuration:",
                        "libav",
                        "Input #",
                        "Metadata:",
                        "Duration:",
                        "Stream #",
                        "Press [q]",
                        "Output #",
                        "Stream mapping:",
                        "frame=",
                        "fps=",
                    ]
                ):
                    # Skip technical output
                    pass
                else:
                    # Only print important messages
                    if line.strip() and not line.strip().startswith("["):
                        logger.debug(f"ffmpeg: {line.strip()}")

            return_code = process.wait()
            if return_code != 0:
                logger.bind(return_code=return_code, operation=operation_name).error(
                    f"FFmpeg exited with code: {return_code} for {operation_name}"
                )
                return False

            logger.bind(operation=operation_name).debug(
                f"{operation_name} completed successfully"
            )
            return True

        except Exception as e:
            logger.bind(error=str(e), operation=operation_name).error(
                f"Error executing FFmpeg command for {operation_name}"
            )
            return False

    def execute_ffprobe_command(
        self, cmd: list, operation_name: str
    ) -> tuple[bool, str, str]:
        """Execute ffprobe command with logging.

        Args:
            cmd: ffprobe command as list
            operation_name: Operation name for logging

        Returns:
            tuple: (success, stdout, stderr)
        """
        try:
            logger.bind(command=" ".join(cmd), operation=operation_name).debug(
                f"Executing ffprobe command for {operation_name}"
            )

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                logger.bind(stderr=stderr, operation=operation_name).error(
                    f"ffprobe failed for {operation_name}"
                )
                return False, stdout, stderr

            logger.bind(operation=operation_name).debug(
                f"{operation_name} completed successfully"
            )
            return True, stdout, stderr

        except Exception as e:
            logger.bind(error=str(e), operation=operation_name).error(
                f"Error executing ffprobe command for {operation_name}"
            )
            return False, "", str(e)

    def extract_frame(
        self,
        video_path: str | Path,
        output_path: str | Path,
        time_seconds: float = 0.0,
    ) -> bool:
        """
        Extracts a frame from a video at a specified time.

        Args:
            video_path: Path to the input video file
            output_path: Path for the extracted frame image
            time_seconds: Time in seconds to extract the frame (default: 0.0)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Base command
            cmd = [self.ffmpeg_path, "-y"]

            # Add input video file
            cmd.extend(["-i", str(video_path)])

            # Seek to the specified time and extract one frame
            cmd.extend(
                [
                    "-ss",
                    str(time_seconds),  # Seek to time
                    "-vframes",
                    "1",  # Extract only one frame
                    "-q:v",
                    "2",  # High quality (scale 1-31, lower is better)
                    str(output_path),
                ]
            )

            # Execute the command using the new method
            success = self.execute_ffmpeg_command(
                cmd,
                "extract frame",
                show_progress=False,  # No progress tracking for single frame extraction
            )

            if success:
                logger.bind(video_path=str(video_path), time_seconds=time_seconds).debug(
                    "frame extracted successfully"
                )
                return True
            else:
                logger.bind(video_path=str(video_path), time_seconds=time_seconds).error(
                    "FFmpeg failed to extract frame"
                )
                return False

        except Exception as e:
            logger.bind(error=str(e)).error("Error extracting frame")
            return False

    def extract_frames(
        self,
        video_path: str | Path,
        output_template: str,
        amount: int = 5,
        length_seconds: float = None,
    ) -> bool:
        """
        Extract multiple frames from a video at regular intervals.

        Args:
            video_path: Path to the input video file
            output_template: Template for output image files (e.g., "frame-%03d.jpg")
            amount: Number of frames to extract (default: 5)
            length_seconds: Length of the video in seconds (optional, if not provided will be calculated)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get video duration if not provided
            if length_seconds is None:
                video_info = self.get_video_info(video_path)
                length_seconds = video_info.get("duration", 0)

            if length_seconds <= 0:
                logger.error("invalid video duration for frame extraction")
                return False

            # Calculate frame interval (time between frames)
            # This gives us the correct fps rate to extract exactly 'amount' frames
            # evenly distributed across the video duration
            frame_interval = length_seconds / amount

            # Base command - using the corrected fps calculation
            # fps=1/frame_interval extracts one frame every frame_interval seconds
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i",
                str(video_path),
                "-vf",
                f"fps=1/{frame_interval}",
                "-vframes",
                str(amount),
                "-qscale:v",
                "2",  # High quality
                output_template,
            ]

            # Execute the command using the new method
            success = self.execute_ffmpeg_command(
                cmd,
                "extract frames",
                show_progress=False,
            )

            if success:
                logger.bind(
                    video_path=str(video_path),
                    amount=amount,
                    frame_interval=frame_interval,
                ).debug("frames extracted successfully")
                return True
            else:
                logger.error("FFmpeg failed to extract frames")
                return False

        except Exception as e:
            logger.bind(error=str(e)).error("Error extracting frames")
            return False

    @staticmethod
    def is_hex_color(color: str) -> bool:
        """
        Checks if the given color string is a valid hex color.

        Args:
            color: Color string to check

        Returns:
            bool: True if it's a hex color, False otherwise
        """
        return all(c in "0123456789abcdefABCDEF" for c in color[1:])

    def colorkey_overlay(
        self,
        input_video_path: str | Path,
        overlay_video_path: str | Path,
        output_video_path: str | Path,
        color: str = "green",
        similarity: float = 0.1,
        blend: float = 0.1,
    ):
        """
        Applies a colorkey overlay to a video using FFmpeg.

        Args:
            input_video_path: Path to base video
            overlay_video_path: Path to overlay video with chroma key
            output_video_path: Path for output video
            color: Color to key out (hex or name, default: green)
            similarity: Color similarity threshold (0.0-1.0)
            blend: Blend amount (0.0-1.0)

        Example command:
            ffmpeg -i input.mp4 -stream_loop -1 -i black_dust.mp4 \
            -filter_complex "[1]colorkey=0x000000:0.1:0.1[ckout];[0][ckout]overlay" \
            -shortest \
            -c:v libx264 -preset ultrafast -crf 18 \
            -c:a copy \
            output.mp4
        """

        start = time.time()
        info = self.get_video_info(input_video_path)
        video_duration = info.get("duration", 0)

        if not video_duration:
            logger.error("failed to get video duration from input video")
            return False

        color = color.lstrip("#")
        if self.is_hex_color(color):
            color = f"0x{color.upper()}"

        context_logger = logger.bind(
            input_video_path=str(input_video_path),
            overlay_video_path=str(overlay_video_path),
            output_video_path=str(output_video_path),
            video_duration=video_duration,
            color=color,
            similarity=similarity,
            blend=blend,
        )
        context_logger.debug("Starting colorkey overlay process")

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i",
            str(input_video_path),
            "-stream_loop",
            "-1",
            "-i",
            str(overlay_video_path),
            "-filter_complex",
            f"[1]colorkey={color}:{similarity}:{blend}[ckout];[0][ckout]overlay",
            "-shortest",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "18",
            "-c:a",
            "copy",
            str(output_video_path),
        ]

        try:
            success = self.execute_ffmpeg_command(
                cmd,
                "colorkey overlay",
                expected_duration=video_duration,
                show_progress=True,
            )

            if success:
                context_logger.bind(execution_time=time.time() - start).debug(
                    "Colorkey overlay successful"
                )
                return True
            else:
                context_logger.error("FFmpeg failed to apply colorkey overlay")
                return False

        except Exception as e:
            context_logger.bind(error=str(e)).error("Error applying colorkey overlay")
            return False

    def convert_pcm_to_wav(
        self,
        input_pcm_path: str | Path,
        output_wav_path: str | Path,
        sample_rate: int = 24000,
        channels: int = 1,
        target_sample_rate: int = 44100,
    ) -> bool:
        """
        Convert PCM audio to WAV format.

        Args:
            input_pcm_path: Path to input PCM file
            output_wav_path: Path for output WAV file
            sample_rate: Input sample rate (default: 24000)
            channels: Input channels (default: 1)
            target_sample_rate: Output sample rate (default: 44100)

        Returns:
            bool: True if successful, False otherwise

        Example command:
            ffmpeg -f s16le -ar 24000 -ac 1 -i out.pcm -ar 44100 -ac 2 out_44k_stereo.wav
        """
        start = time.time()
        context_logger = logger.bind(
            input_pcm_path=str(input_pcm_path),
            output_wav_path=str(output_wav_path),
            sample_rate=sample_rate,
            channels=channels,
            target_sample_rate=target_sample_rate,
        )
        context_logger.debug("Starting PCM to WAV conversion")

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-f",
            "s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            "-i",
            str(input_pcm_path),
            "-ar",
            str(target_sample_rate),
            "-ac",
            "2",  # Convert to stereo
            str(output_wav_path),
        ]

        try:
            success = self.execute_ffmpeg_command(
                cmd,
                "convert PCM to WAV",
                show_progress=False,
            )

            if success:
                context_logger.bind(execution_time=time.time() - start).debug(
                    "PCM to WAV conversion successful",
                )
                return True
            else:
                context_logger.error("ffmpeg failed to convert PCM to WAV")
                return False

        except Exception as e:
            context_logger.bind(error=str(e)).error(
                "error converting PCM to WAV",
            )
            return False


__all__ = ["MediaUtils"]

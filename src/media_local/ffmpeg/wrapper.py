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

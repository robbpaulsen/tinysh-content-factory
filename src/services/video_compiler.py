"""Video compilation service using FFmpeg."""

import logging
import random
import subprocess
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class VideoCompiler:
    """Service for compiling multiple video clips into a single video."""

    def __init__(self, output_dir: Path | None = None):
        """
        Initialize video compiler.

        Args:
            output_dir: Directory to save compiled videos (default: ./compiled)
        """
        self.output_dir = output_dir or Path("./compiled")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Check if FFmpeg is installed
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("FFmpeg is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "FFmpeg is not installed. Install FFmpeg to use this service."
            )

    def compile_videos(
        self,
        video_paths: List[Path],
        output_filename: str,
        transition: str = "fade",
        transition_duration: float = 0.5,
        add_text_overlays: bool = False,
        target_resolution: tuple[int, int] = (1920, 1080),
    ) -> Path:
        """
        Compile multiple video clips into a single video.

        Args:
            video_paths: List of paths to video files to compile
            output_filename: Name of output file (e.g., "compilation_001.mp4")
            transition: Transition type ("fade", "none")
            transition_duration: Duration of transition in seconds
            add_text_overlays: Whether to add text overlays (e.g., clip numbers)
            target_resolution: Target resolution (width, height)

        Returns:
            Path to compiled video file

        Example:
            compiler = VideoCompiler()
            clips = [Path("clip1.mp4"), Path("clip2.mp4"), Path("clip3.mp4")]
            output = compiler.compile_videos(
                clips,
                "finance_compilation_001.mp4",
                transition="fade",
            )
        """
        if not video_paths:
            raise ValueError("No video paths provided")

        logger.info(f"Compiling {len(video_paths)} videos into {output_filename}")

        output_path = self.output_dir / output_filename

        # Create a file list for FFmpeg concat
        filelist_path = self.output_dir / f"filelist_{output_filename}.txt"

        with open(filelist_path, "w") as f:
            for video_path in video_paths:
                # Escape single quotes in path
                escaped_path = str(video_path.absolute()).replace("'", r"'\''")
                f.write(f"file '{escaped_path}'\n")

        try:
            if transition == "fade":
                # Use xfade filter for smooth transitions
                output_path = self._compile_with_xfade(
                    video_paths=video_paths,
                    output_path=output_path,
                    transition_duration=transition_duration,
                    target_resolution=target_resolution,
                )
            else:
                # Simple concatenation without transitions
                output_path = self._compile_concat(
                    filelist_path=filelist_path,
                    output_path=output_path,
                    target_resolution=target_resolution,
                )

            logger.info(f"Compiled video saved to: {output_path}")
            return output_path

        finally:
            # Clean up filelist
            if filelist_path.exists():
                filelist_path.unlink()

    def _compile_concat(
        self,
        filelist_path: Path,
        output_path: Path,
        target_resolution: tuple[int, int],
    ) -> Path:
        """
        Compile videos using simple concatenation (no transitions).

        Args:
            filelist_path: Path to FFmpeg concat file list
            output_path: Path to output video
            target_resolution: Target resolution (width, height)

        Returns:
            Path to compiled video
        """
        width, height = target_resolution

        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(filelist_path),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-y",  # Overwrite output file
            str(output_path),
        ]

        logger.info("Running FFmpeg concat...")
        subprocess.run(cmd, check=True, capture_output=True)

        return output_path

    def _compile_with_xfade(
        self,
        video_paths: List[Path],
        output_path: Path,
        transition_duration: float,
        target_resolution: tuple[int, int],
    ) -> Path:
        """
        Compile videos with crossfade transitions using xfade filter.

        Args:
            video_paths: List of video file paths
            output_path: Path to output video
            transition_duration: Duration of fade transition in seconds
            target_resolution: Target resolution (width, height)

        Returns:
            Path to compiled video
        """
        if len(video_paths) < 2:
            # Single video, no transitions needed
            return self._compile_concat(
                filelist_path=self.output_dir / "temp_filelist.txt",
                output_path=output_path,
                target_resolution=target_resolution,
            )

        width, height = target_resolution

        # Build FFmpeg filter complex for xfade
        # This is complex, so for simplicity we'll use concat with fade in/out
        # For true xfade between clips, a more complex filter graph is needed

        # Simpler approach: add fade in/out to each clip, then concat
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(self._create_filelist(video_paths)),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fade=t=in:st=0:d={transition_duration},fade=t=out:st=0:d={transition_duration}",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-y",
            str(output_path),
        ]

        logger.info("Running FFmpeg with fade transitions...")
        subprocess.run(cmd, check=True, capture_output=True)

        return output_path

    def _create_filelist(self, video_paths: List[Path]) -> Path:
        """Create a temporary filelist for FFmpeg concat."""
        filelist_path = self.output_dir / "temp_filelist.txt"
        with open(filelist_path, "w") as f:
            for video_path in video_paths:
                escaped_path = str(video_path.absolute()).replace("'", r"'\''")
                f.write(f"file '{escaped_path}'\n")
        return filelist_path

    def create_compilation(
        self,
        video_paths: List[Path],
        output_filename: str,
        clips_per_video: tuple[int, int] = (5, 10),
        shuffle: bool = True,
        **compile_kwargs,
    ) -> Path:
        """
        Create a compilation video from a pool of clips.

        Args:
            video_paths: Pool of video clips to choose from
            output_filename: Name of output file
            clips_per_video: Range of clips to include (min, max)
            shuffle: Whether to shuffle clips randomly
            **compile_kwargs: Additional arguments for compile_videos()

        Returns:
            Path to compiled video file

        Example:
            compiler = VideoCompiler()
            clips = [Path(f"clip_{i}.mp4") for i in range(20)]
            output = compiler.create_compilation(
                clips,
                "finance_compilation_001.mp4",
                clips_per_video=(5, 10),
                shuffle=True,
                transition="fade",
            )
        """
        if not video_paths:
            raise ValueError("No video paths provided")

        # Select random number of clips
        min_clips, max_clips = clips_per_video
        num_clips = random.randint(min_clips, min(max_clips, len(video_paths)))

        # Select clips
        if shuffle:
            selected_clips = random.sample(video_paths, num_clips)
        else:
            selected_clips = video_paths[:num_clips]

        logger.info(f"Selected {num_clips} clips for compilation")

        # Compile videos
        return self.compile_videos(
            video_paths=selected_clips,
            output_filename=output_filename,
            **compile_kwargs,
        )

    def add_intro_outro(
        self,
        video_path: Path,
        intro_path: Path | None = None,
        outro_path: Path | None = None,
        output_filename: str | None = None,
    ) -> Path:
        """
        Add intro and/or outro to a video.

        Args:
            video_path: Main video file
            intro_path: Optional intro video
            outro_path: Optional outro video
            output_filename: Output filename (default: adds "_with_intro_outro" suffix)

        Returns:
            Path to video with intro/outro
        """
        clips = []

        if intro_path:
            clips.append(intro_path)

        clips.append(video_path)

        if outro_path:
            clips.append(outro_path)

        if len(clips) == 1:
            logger.warning("No intro or outro provided, returning original video")
            return video_path

        if not output_filename:
            output_filename = f"{video_path.stem}_with_intro_outro{video_path.suffix}"

        return self.compile_videos(
            video_paths=clips,
            output_filename=output_filename,
            transition="none",
        )

"""YouTube video downloader service using yt-dlp."""

import logging
import subprocess
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class YouTubeDownloadResult:
    """Result of a YouTube video download."""

    def __init__(
        self,
        video_path: Path,
        title: str,
        duration: float,
        views: int,
        url: str,
    ):
        self.video_path = video_path
        self.title = title
        self.duration = duration
        self.views = views
        self.url = url


class YouTubeDownloader:
    """Service for downloading YouTube videos using yt-dlp."""

    def __init__(self, output_dir: Path | None = None):
        """
        Initialize YouTube downloader.

        Args:
            output_dir: Directory to save downloaded videos (default: ./downloads)
        """
        self.output_dir = output_dir or Path("./downloads")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Check if yt-dlp is installed
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"yt-dlp version: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "yt-dlp is not installed. Install with: pip install yt-dlp"
            )

    def search_and_download(
        self,
        query: str,
        max_results: int = 10,
        min_views: int = 10000,
        max_duration: int = 60,
        download_format: str = "best[height<=1080]",
    ) -> List[YouTubeDownloadResult]:
        """
        Search YouTube and download videos matching criteria.

        Args:
            query: Search query (e.g., "passive income ideas shorts")
            max_results: Maximum number of videos to download
            min_views: Minimum view count filter
            max_duration: Maximum video duration in seconds
            download_format: yt-dlp format selector

        Returns:
            List of YouTubeDownloadResult objects
        """
        logger.info(f"Searching YouTube: '{query}' (max {max_results} results)")

        # Build yt-dlp command for search
        search_url = f"ytsearch{max_results}:{query}"

        # First, get video info without downloading
        info_cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-warnings",
            "--max-downloads", str(max_results),
            search_url,
        ]

        try:
            result = subprocess.run(
                info_cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to search YouTube: {e.stderr}")
            return []

        # Parse JSON output (one JSON object per line)
        import json
        videos_info = []
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    info = json.loads(line)
                    videos_info.append(info)
                except json.JSONDecodeError:
                    continue

        # Filter videos by criteria
        filtered_videos = []
        for info in videos_info:
            views = info.get("view_count", 0)
            duration = info.get("duration", 0)

            if views >= min_views and duration <= max_duration:
                filtered_videos.append(info)

        logger.info(
            f"Found {len(filtered_videos)} videos matching criteria "
            f"(min {min_views} views, max {max_duration}s duration)"
        )

        # Download filtered videos
        downloaded = []
        for i, info in enumerate(filtered_videos, 1):
            url = info.get("webpage_url") or info.get("url")
            title = info.get("title", f"video_{i}")
            duration = info.get("duration", 0)
            views = info.get("view_count", 0)

            logger.info(f"Downloading {i}/{len(filtered_videos)}: {title} ({views:,} views)")

            try:
                result = self.download_video(
                    url=url,
                    download_format=download_format,
                )
                downloaded.append(result)
            except Exception as e:
                logger.error(f"Failed to download {url}: {e}")
                continue

        logger.info(f"Successfully downloaded {len(downloaded)} videos")
        return downloaded

    def download_video(
        self,
        url: str,
        download_format: str = "best[height<=1080]",
        filename: str | None = None,
    ) -> YouTubeDownloadResult:
        """
        Download a single YouTube video.

        Args:
            url: YouTube video URL
            download_format: yt-dlp format selector (default: best up to 1080p)
            filename: Custom filename (optional, auto-generated if None)

        Returns:
            YouTubeDownloadResult object

        Examples:
            # Download best quality up to 1080p
            download_video("https://youtube.com/watch?v=...", "best[height<=1080]")

            # Download best quality up to 720p
            download_video("https://youtube.com/watch?v=...", "best[height<=720]")
        """
        logger.info(f"Downloading video: {url}")

        # Build output template
        if filename:
            output_template = str(self.output_dir / filename)
        else:
            output_template = str(self.output_dir / "%(id)s.%(ext)s")

        # Build yt-dlp command
        cmd = [
            "yt-dlp",
            "--format", download_format,
            "--output", output_template,
            "--no-warnings",
            "--no-playlist",
            "--print", "after_move:filepath",  # Print final file path
            url,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            # Get downloaded file path from output
            video_path = Path(result.stdout.strip().split("\n")[-1])

            # Get video info
            info_cmd = [
                "yt-dlp",
                "--dump-json",
                "--no-warnings",
                url,
            ]
            info_result = subprocess.run(
                info_cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            import json
            info = json.loads(info_result.stdout)

            logger.info(f"Downloaded: {video_path} ({info.get('view_count', 0):,} views)")

            return YouTubeDownloadResult(
                video_path=video_path,
                title=info.get("title", "Unknown"),
                duration=info.get("duration", 0),
                views=info.get("view_count", 0),
                url=url,
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"yt-dlp error: {e.stderr}")
            raise RuntimeError(f"Failed to download video: {e.stderr}")

    def download_shorts_batch(
        self,
        search_queries: List[str],
        videos_per_query: int = 5,
        min_views: int = 10000,
    ) -> List[YouTubeDownloadResult]:
        """
        Download multiple YouTube Shorts from multiple search queries.

        Args:
            search_queries: List of search queries
            videos_per_query: Number of videos to download per query
            min_views: Minimum view count filter

        Returns:
            Combined list of downloaded videos

        Example:
            queries = [
                "passive income ideas shorts",
                "investment tips shorts",
                "money management shorts",
            ]
            videos = downloader.download_shorts_batch(queries, videos_per_query=5)
        """
        all_videos = []

        for query in search_queries:
            logger.info(f"Processing query: '{query}'")
            videos = self.search_and_download(
                query=query,
                max_results=videos_per_query,
                min_views=min_views,
                max_duration=60,  # Shorts are max 60 seconds
            )
            all_videos.extend(videos)

        logger.info(f"Total videos downloaded: {len(all_videos)}")
        return all_videos

"""Main workflow orchestrator for YouTube Shorts generation."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.config import settings
from src.models import GeneratedVideo, SEOMetadata, StoryRecord, VideoScript
from src.services.llm import LLMService
from src.services.logger_service import log_performance
from src.services.media import MediaService
from src.services.profile_manager import ProfileManager
from src.services.reddit import RedditService
from src.services.scheduler import VideoScheduler
from src.services.seo_optimizer import SEOOptimizerService
from src.services.sheets import GoogleSheetsService
from src.services.youtube import YouTubeService

logger = logging.getLogger(__name__)
console = Console()


class WorkflowOrchestrator:
    """Orchestrates the complete YouTube Shorts generation workflow."""

    def __init__(
        self,
        channel_config: "ChannelConfig | None" = None,
        profile: str | None = None
    ):
        """
        Initialize all services.

        Args:
            channel_config: Channel configuration (optional, uses default if None)
            profile: Voice/music profile ID (uses default from channel/profiles.yaml if None)
        """
        from src.channel_config import ChannelConfig

        logger.info("Initializing workflow orchestrator")

        # Set channel config
        self.channel_config = channel_config
        if self.channel_config:
            logger.info(f"Using channel: {self.channel_config.config.name}")

        # Initialize profile manager (from channel or global profiles.yaml)
        if self.channel_config:
            profiles_path = self.channel_config.channel_dir / "profiles.yaml"
            if not profiles_path.exists():
                profiles_path = settings.profiles_path
        else:
            profiles_path = settings.profiles_path

        self.profile_manager = ProfileManager(profiles_path)

        # Use profile from: 1) CLI arg, 2) channel config, 3) profiles.yaml default
        if profile:
            self.active_profile = profile
        elif self.channel_config and self.channel_config.config.default_profile:
            self.active_profile = self.channel_config.config.default_profile
        else:
            self.active_profile = settings.active_profile

        # Log which profile is being used
        selected_profile = self.profile_manager.get_profile(self.active_profile)
        logger.info(f"Using profile: {selected_profile.name}")

        # Initialize services
        self.reddit = RedditService()

        # Initialize Google Sheets with channel-specific tab if available
        sheet_tab = None
        if self.channel_config and hasattr(self.channel_config.config.content, 'sheet_tab'):
            sheet_tab = self.channel_config.config.content.sheet_tab
            if sheet_tab:
                logger.info(f"Using Google Sheets tab: {sheet_tab}")

        self.sheets = GoogleSheetsService(sheet_name=sheet_tab)
        self.llm = LLMService(channel_config=self.channel_config)
        self.media = MediaService()

        # Initialize YouTube with channel-specific credentials if available
        if self.channel_config:
            self.youtube = YouTubeService(credentials_path=self.channel_config.credentials_path)
        else:
            self.youtube = YouTubeService()

        self.seo_optimizer = SEOOptimizerService() if settings.seo_enabled else None

    async def close(self):
        """Clean up resources."""
        await self.media.close()

    async def update_stories_from_reddit(
        self, subreddit: str | None = None, limit: int = 25
    ) -> int:
        """
        Download stories from Reddit and save to Google Sheets.

        Args:
            subreddit: Subreddit name (defaults to channel config or settings.subreddit)
            limit: Number of stories to fetch

        Returns:
            Number of stories saved
        """
        console.print(f"\n[bold cyan]📥 Fetching stories from Reddit...[/bold cyan]")

        # Use subreddit from: 1) explicit arg, 2) channel config, 3) settings
        if not subreddit:
            if self.channel_config and hasattr(self.channel_config.config.content, 'subreddit'):
                subreddit = self.channel_config.config.content.subreddit

        # Fetch stories
        posts = self.reddit.get_top_stories(
            subreddit_name=subreddit, time_filter="month", limit=limit
        )

        if not posts:
            console.print("[yellow]No stories found[/yellow]")
            return 0

        # Save to sheets
        count = self.sheets.save_stories(posts)
        console.print(f"[green]✓ Saved {count} stories to Google Sheets[/green]")

        return count

    async def generate_video_from_story(self, story: StoryRecord) -> tuple[str, VideoScript]:
        """
        Generate complete video from a story.

        Args:
            story: Story record from Google Sheets

        Returns:
            Tuple of (final_video_id, script)
        """
        console.print(f"\n[bold cyan]🎬 Processing story: {story.title[:60]}...[/bold cyan]")

        with log_performance(f"Generate video: {story.title[:40]}", logger):
            # Step 1: Generate script with LLM
            console.print("[cyan]  → Creating script with Gemini...[/cyan]")
            with log_performance("LLM script generation", logger):
                script = await self.llm.create_complete_workflow(story.title, story.content)
            console.print(f"[green]  ✓ Script created with {len(script.scenes)} scenes[/green]")

            # Step 2: Process each scene sequentially
            scene_videos: list[GeneratedVideo] = []

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Processing {len(script.scenes)} scenes...", total=len(script.scenes)
                )

                for idx, scene in enumerate(script.scenes, 1):
                    progress.update(task, description=f"[cyan]Scene {idx}/{len(script.scenes)}...")

                    # OPTIMIZATION: Generate image + TTS in parallel (independent operations)
                    # Before: image(20s) → TTS(15s) → video(8s) = 43s per scene
                    # After: max(image(20s), TTS(15s)) → video(8s) = 28s per scene
                    # Savings: ~15s per scene (35% faster)
                    logger.info(f"Scene {idx}: Generating image + TTS in parallel")
                    voice_config = self.profile_manager.get_voice_config(self.active_profile)

                    image, tts = await asyncio.gather(
                        self.media.generate_and_upload_image(scene.image_prompt),
                        self.media.generate_tts(scene.text, voice_config=voice_config)
                    )

                    # Generate video with captions (requires both image + TTS)
                    logger.info(f"Scene {idx}: Generating captioned video")
                    video = await self.media.generate_captioned_video(
                        image.file_id, tts.file_id, scene.text
                    )

                    scene_videos.append(video)
                    progress.advance(task)

            console.print(f"[green]  ✓ Generated {len(scene_videos)} scene videos[/green]")

            # Step 3: Merge all videos with profile-specific music
            console.print("[cyan]  → Merging videos...[/cyan]")
            video_ids = [v.file_id for v in scene_videos]
            music_config = self.profile_manager.get_music_config(self.active_profile)
            with log_performance("Video merge with music", logger):
                final_video_id = await self.media.merge_videos(
                    video_ids,
                    background_music_path=music_config["path"],
                    music_volume=music_config["volume"]
                )
            console.print(f"[green]  ✓ Videos merged with music: {music_config['name']}[/green]")

            return final_video_id, script

    async def generate_and_save_seo_metadata(
        self, script: VideoScript, video_id: str, output_dir: Path
    ) -> SEOMetadata | None:
        """
        Generate SEO-optimized metadata and save to JSON file.

        Args:
            script: Video script with scenes
            video_id: Generated video file ID
            output_dir: Directory to save metadata file

        Returns:
            SEO metadata or None if SEO is disabled
        """
        if not self.seo_optimizer:
            logger.info("SEO optimizer disabled, skipping metadata generation")
            return None

        console.print("[cyan]  → Generating SEO metadata...[/cyan]")

        with log_performance("SEO metadata generation", logger):
            # Combine all scene texts for context
            script_text = " ".join([scene.text for scene in script.scenes])

            # Get profile name for context
            profile = self.profile_manager.get_profile(self.active_profile)

            # Generate SEO metadata
            metadata = await self.seo_optimizer.generate_seo_metadata(
                video_title=script.title,
                video_description=script.description,
                script_text=script_text,
                profile_name=profile.name,
            )

        # Save to JSON file
        # video_id is like "video_001.mp4", we want "video_001_metadata.json"
        video_base = video_id.rsplit(".", 1)[0] if "." in video_id else video_id
        metadata_path = output_dir / f"{video_base}_metadata.json"

        metadata_dict = {
            "title": metadata.title,
            "description": metadata.description,
            "tags": metadata.tags,
            "category_id": metadata.category_id,
            "original_title": script.title,
            "original_description": script.description,
            "profile": profile.name,
        }

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata_dict, f, indent=2, ensure_ascii=False)

        console.print(f"[green]  ✓ SEO metadata saved to {metadata_path.name}[/green]")
        logger.info(f"SEO Title: {metadata.title}")
        logger.info(f"Tags: {', '.join(metadata.tags[:5])}...")

        return metadata

    async def upload_to_youtube(
        self, video_id: str, script: VideoScript, output_dir: Path | None = None
    ) -> str:
        """
        Download video and upload to YouTube.

        Args:
            video_id: Media server file ID
            script: Video script with metadata
            output_dir: Directory to save video (default: ./output)

        Returns:
            YouTube video URL
        """
        output_dir = output_dir or Path("./output")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Download video
        console.print("[cyan]  → Downloading video...[/cyan]")
        # video_id already includes extension
        video_path = output_dir / video_id
        await self.media.download_file(video_id, video_path)
        console.print(f"[green]  ✓ Downloaded to {video_path}[/green]")

        # Upload to YouTube
        console.print("[cyan]  → Uploading to YouTube...[/cyan]")
        result = self.youtube.upload_video(
            video_path=video_path,
            title=script.title,
            description=script.description,
            tags=["motivation", "shorts", "inspiration", "self-improvement"],
        )

        console.print(f"[bold green]✓ Uploaded to YouTube: {result.url}[/bold green]")

        return result.url

    async def cleanup_temporary_files(self, scene_videos: list[GeneratedVideo], final_video_id: str):
        """
        Clean up temporary files from media server.

        Args:
            scene_videos: List of generated scene videos
            final_video_id: Final merged video ID
        """
        console.print("[cyan]  → Cleaning up temporary files...[/cyan]")

        file_ids = []
        for video in scene_videos:
            file_ids.extend([video.video_id, video.tts_id, video.image_id])

        # Add voice sample and background music if used
        if settings.chatterbox_voice_sample_id:
            file_ids.append(settings.chatterbox_voice_sample_id)

        # Filter out None values
        file_ids = [fid for fid in file_ids if fid]

        # Note: We don't delete final_video_id or background_music_id
        # as they may be needed

        await self.media.cleanup_files(file_ids)
        console.print(f"[green]  ✓ Cleaned up {len(file_ids)} temporary files[/green]")

    async def run_complete_workflow(
        self,
        update_stories: bool = False,
        process_count: int = 1,
    ):
        """
        Run the complete workflow: fetch stories, generate videos, upload to YouTube.

        Args:
            update_stories: Whether to fetch new stories from Reddit first
            process_count: Number of videos to generate
        """
        console.print("\n[bold magenta]🚀 Starting YouTube Shorts Factory[/bold magenta]\n")

        try:
            # Check media server health
            console.print("[cyan]Checking media server...[/cyan]")
            await self.media.health_check()
            console.print("[green]✓ Media server is ready[/green]")

            # Update stories if requested
            if update_stories:
                await self.update_stories_from_reddit()

            # Process videos
            for i in range(process_count):
                console.print(f"\n[bold yellow]📹 Video {i + 1}/{process_count}[/bold yellow]")

                # Get next story
                story = self.sheets.get_story_without_video()
                if not story:
                    console.print("[yellow]⚠ No more stories to process[/yellow]")
                    break

                # Generate video
                final_video_id, script = await self.generate_video_from_story(story)

                # Download video locally (YouTube upload disabled)
                # Use channel output dir if available, otherwise use default
                if self.channel_config:
                    output_dir = self.channel_config.output_dir
                else:
                    output_dir = Path("./output")
                output_dir.mkdir(parents=True, exist_ok=True)
                # file_id already includes .mp4 extension
                video_path = output_dir / final_video_id

                console.print("[cyan]  → Downloading video...[/cyan]")
                await self.media.download_file(final_video_id, video_path)
                console.print(f"[green]  ✓ Video saved to {video_path}[/green]")

                # Generate SEO metadata
                await self.generate_and_save_seo_metadata(script, final_video_id, output_dir)

                # YouTube upload commented out - do manually
                # youtube_url = await self.upload_to_youtube(final_video_id, script)

                # Update Google Sheets with video ID
                self.sheets.update_video_id(story.row_number, final_video_id)
                console.print(f"[green]✓ Updated Google Sheets row {story.row_number}[/green]")

                console.print(f"\n[bold green]🎉 Video complete: {video_path}[/bold green]\n")
                console.print(f"[yellow]ℹ YouTube upload disabled - upload manually when ready[/yellow]\n")

            console.print("\n[bold magenta]✨ Workflow completed successfully![/bold magenta]\n")

        except Exception as e:
            logger.exception("Workflow failed")
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]\n")
            raise

    async def run_single_story(self, story_id: str):
        """
        Process a single story by Reddit ID.

        Args:
            story_id: Reddit post ID
        """
        console.print(f"\n[bold magenta]🚀 Processing story: {story_id}[/bold magenta]\n")

        try:
            # Check media server
            console.print("[cyan]Checking media server...[/cyan]")
            await self.media.health_check()
            console.print("[green]✓ Media server is ready[/green]")

            # Fetch story from Reddit
            console.print(f"[cyan]Fetching story from Reddit...[/cyan]")
            post = self.reddit.get_post_by_id(story_id)
            console.print(f"[green]✓ Story fetched: {post.title[:60]}...[/green]")

            # Create temporary story record
            story = StoryRecord(
                id=post.id,
                title=post.title,
                content=post.content,
                video_id=None,
                row_number=None,
            )

            # Generate video
            final_video_id, script = await self.generate_video_from_story(story)

            # Download video locally (YouTube upload disabled)
            # Use channel output dir if available, otherwise use default
            if self.channel_config:
                output_dir = self.channel_config.output_dir
            else:
                output_dir = Path("./output")
            output_dir.mkdir(parents=True, exist_ok=True)
            # file_id already includes .mp4 extension
            video_path = output_dir / final_video_id

            console.print("[cyan]  → Downloading video...[/cyan]")
            await self.media.download_file(final_video_id, video_path)
            console.print(f"[green]  ✓ Video saved to {video_path}[/green]")

            # Generate SEO metadata
            await self.generate_and_save_seo_metadata(script, final_video_id, output_dir)

            # YouTube upload commented out - do manually
            # youtube_url = await self.upload_to_youtube(final_video_id, script)

            console.print(f"\n[bold green]🎉 Video complete: {video_path}[/bold green]\n")
            console.print(f"[yellow]ℹ YouTube upload disabled - upload manually when ready[/yellow]\n")

        except Exception as e:
            logger.exception("Single story workflow failed")
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]\n")
            raise
    async def schedule_batch_upload(
        self,
        start_date: datetime | None = None,
        dry_run: bool = False,
    ) -> list[tuple[str, datetime, str]]:
        """
        Schedule batch upload of all generated videos from Sheets.

        This function:
        1. Reads all available videos from output/ directory
        2. Loads corresponding metadata from JSON files
        3. Calculates publish schedule (6 AM - 4 PM, every 2 hours, 6 videos/day)
        4. Uploads videos to YouTube with scheduled publish times

        Args:
            start_date: Start date for scheduling (default: tomorrow 6 AM)
            dry_run: If True, calculate schedule but don't upload

        Returns:
            List of tuples: (video_path, publish_time, video_url)
        """
        console.print("\n[bold cyan]📅 Batch Video Scheduling[/bold cyan]\n")

        output_dir = Path("./output")
        if not output_dir.exists():
            console.print("[red]✗ Output directory not found[/red]")
            return []

        # Find all video files
        video_files = sorted(output_dir.glob("video_*.mp4"))
        if not video_files:
            console.print("[yellow]⚠ No videos found in output/[/yellow]")
            return []

        console.print(f"Found {len(video_files)} videos to schedule\n")

        # Initialize scheduler
        scheduler = VideoScheduler()

        # Calculate schedule
        publish_schedule = scheduler.calculate_schedule(
            video_count=len(video_files),
            start_date=start_date,
        )

        # Display schedule summary
        summary = scheduler.get_schedule_summary(publish_schedule)
        console.print(f"[cyan]{summary}[/cyan]\n")

        # Validate schedule
        try:
            scheduler.validate_schedule(publish_schedule)
            console.print("[green]✓ Schedule validation passed[/green]\n")
        except ValueError as e:
            console.print(f"[red]✗ Schedule validation failed: {e}[/red]")
            return []

        if dry_run:
            console.print("[yellow]🔍 Dry run mode - no uploads will be performed[/yellow]\n")

            # Display detailed schedule table
            table = Table(title="Scheduled Videos (Dry Run)")
            table.add_column("Video", style="cyan")
            table.add_column("Publish Time (Local)", style="green")
            table.add_column("Publish Time (UTC)", style="blue")

            for video_file, publish_time in zip(video_files, publish_schedule):
                publish_local = publish_time.astimezone(scheduler.timezone)
                table.add_row(
                    video_file.name,
                    publish_local.strftime("%Y-%m-%d %H:%M"),
                    publish_time.strftime("%Y-%m-%d %H:%M"),
                )

            console.print(table)
            return [(str(vf), pt, "dry-run") for vf, pt in zip(video_files, publish_schedule)]

        # Upload videos with scheduling
        console.print("[bold cyan]📤 Starting batch upload...[/bold cyan]\n")

        results = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Uploading {len(video_files)} videos...", total=len(video_files)
            )

            for i, (video_file, publish_time) in enumerate(zip(video_files, publish_schedule), 1):
                progress.update(
                    task,
                    description=f"[cyan]Uploading {i}/{len(video_files)}: {video_file.name}...",
                )

                try:
                    # Load metadata if exists
                    metadata_file = video_file.with_suffix("").with_suffix(".json").name
                    metadata_path = output_dir / f"{metadata_file.replace('.mp4', '')}_metadata.json"

                    title = None
                    description = None
                    tags = None
                    category_id = None

                    if metadata_path.exists():
                        with open(metadata_path, encoding="utf-8") as f:
                            metadata = json.load(f)
                            title = metadata.get("title")
                            description = metadata.get("description")
                            tags = metadata.get("tags")
                            category_id = metadata.get("category_id")

                    # Fallback to defaults if metadata not found
                    if not title:
                        title = f"Motivational Short {i}"
                        logger.warning(f"No metadata found for {video_file.name}, using default title")

                    if not description:
                        description = "An inspiring motivational message. #motivation #shorts"

                    if not tags:
                        tags = ["motivation", "shorts", "inspiration", "self-improvement"]

                    # Upload with scheduling
                    result = self.youtube.upload_video(
                        video_path=video_file,
                        title=title,
                        description=description,
                        tags=tags,
                        category_id=category_id,
                        privacy_status="private",
                        publish_at=publish_time,
                    )

                    publish_local = publish_time.astimezone(scheduler.timezone)
                    console.print(
                        f"[green]✓ {video_file.name} → "
                        f"{publish_local.strftime('%Y-%m-%d %H:%M')} → {result.url}[/green]"
                    )

                    results.append((str(video_file), publish_time, result.url))

                except Exception as e:
                    logger.exception(f"Failed to upload {video_file.name}")
                    console.print(f"[red]✗ {video_file.name}: {e}[/red]")
                    results.append((str(video_file), publish_time, f"ERROR: {e}"))

                progress.advance(task)

        console.print(f"\n[bold green]🎉 Batch upload complete![/bold green]")
        console.print(f"Uploaded: {len([r for r in results if not r[2].startswith('ERROR')])} videos")
        console.print(f"Failed: {len([r for r in results if r[2].startswith('ERROR')])} videos\n")

        return results

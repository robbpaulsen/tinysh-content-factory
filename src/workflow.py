"""Main workflow orchestrator for YouTube Shorts generation."""

import asyncio
import logging
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config import settings
from src.models import GeneratedVideo, StoryRecord, VideoScript
from src.services.llm import LLMService
from src.services.media import MediaService
from src.services.reddit import RedditService
from src.services.sheets import GoogleSheetsService
from src.services.youtube import YouTubeService

logger = logging.getLogger(__name__)
console = Console()


class WorkflowOrchestrator:
    """Orchestrates the complete YouTube Shorts generation workflow."""

    def __init__(self):
        """Initialize all services."""
        logger.info("Initializing workflow orchestrator")

        self.reddit = RedditService()
        self.sheets = GoogleSheetsService()
        self.llm = LLMService()
        self.media = MediaService()
        self.youtube = YouTubeService()

    async def close(self):
        """Clean up resources."""
        await self.media.close()

    async def update_stories_from_reddit(
        self, subreddit: str | None = None, limit: int = 25
    ) -> int:
        """
        Download stories from Reddit and save to Google Sheets.

        Args:
            subreddit: Subreddit name (defaults to settings.subreddit)
            limit: Number of stories to fetch

        Returns:
            Number of stories saved
        """
        console.print(f"\n[bold cyan]📥 Fetching stories from Reddit...[/bold cyan]")

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

        # Step 1: Generate script with LLM
        console.print("[cyan]  → Creating script with Gemini...[/cyan]")
        script = await self.llm.create_complete_workflow(story.title, story.content)
        console.print(f"[green]  ✓ Script created with {len(script.scenes)} scenes[/green]")

        # Step 2: Process each scene
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

                # Generate image
                logger.info(f"Scene {idx}: Generating image")
                image = await self.media.generate_and_upload_image(scene.image_prompt)

                # Generate TTS
                logger.info(f"Scene {idx}: Generating TTS")
                tts = await self.media.generate_tts(scene.text)

                # Generate video with captions
                logger.info(f"Scene {idx}: Generating captioned video")
                video = await self.media.generate_captioned_video(
                    image.file_id, tts.file_id, scene.text
                )

                scene_videos.append(video)
                progress.advance(task)

        console.print(f"[green]  ✓ Generated {len(scene_videos)} scene videos[/green]")

        # Step 3: Merge all videos
        console.print("[cyan]  → Merging videos...[/cyan]")
        video_ids = [v.file_id for v in scene_videos]
        final_video_id = await self.media.merge_videos(
            video_ids, background_music_id=settings.background_music_id
        )
        console.print(f"[green]  ✓ Videos merged: {final_video_id}[/green]")

        return final_video_id, script

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
        video_path = output_dir / f"{video_id}.mp4"
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
                output_dir = Path("./output")
                output_dir.mkdir(parents=True, exist_ok=True)
                video_path = output_dir / f"{final_video_id}.mp4"

                console.print("[cyan]  → Downloading video...[/cyan]")
                await self.media.download_file(final_video_id, video_path)
                console.print(f"[green]  ✓ Video saved to {video_path}[/green]")

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
            output_dir = Path("./output")
            output_dir.mkdir(parents=True, exist_ok=True)
            video_path = output_dir / f"{final_video_id}.mp4"

            console.print("[cyan]  → Downloading video...[/cyan]")
            await self.media.download_file(final_video_id, video_path)
            console.print(f"[green]  ✓ Video saved to {video_path}[/green]")

            # YouTube upload commented out - do manually
            # youtube_url = await self.upload_to_youtube(final_video_id, script)

            console.print(f"\n[bold green]🎉 Video complete: {video_path}[/bold green]\n")
            console.print(f"[yellow]ℹ YouTube upload disabled - upload manually when ready[/yellow]\n")

        except Exception as e:
            logger.exception("Single story workflow failed")
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]\n")
            raise

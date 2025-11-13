"""Main CLI entry point for YouTube Shorts Factory."""

import asyncio
import logging
import sys
from pathlib import Path

import click
from rich.console import Console

from src.services.logger_service import cleanup_old_logs, setup_logging
from src.workflow import WorkflowOrchestrator

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose (DEBUG) logging",
)
@click.pass_context
def cli(ctx, verbose: bool):
    """
    YouTube Shorts Factory - Automated video generation from Reddit stories.

    Transform Reddit stories into engaging YouTube Shorts with AI-generated
    content, images, voiceovers, and captions.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    # Setup logging based on verbose flag
    setup_logging(verbose=verbose)

    # Cleanup old logs on startup
    from src.config import settings
    cleanup_old_logs(max_age_days=settings.log_max_age_days)


@cli.command()
def list_channels():
    """List all available channels and their configurations."""
    from rich.table import Table
    from src.channel_config import ChannelConfig

    console.print("\n[bold cyan]📺 Available Channels[/bold cyan]\n")

    channels = ChannelConfig.list_available_channels()

    if not channels:
        console.print("[yellow]No channels found in channels/ directory[/yellow]")
        console.print("\nRun: python -m src.main init-channel --name <channel_name>")
        return

    table = Table(title="Configured Channels")
    table.add_column("Channel", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Handle", style="blue")
    table.add_column("Format", style="magenta")

    for channel_name in channels:
        try:
            config = ChannelConfig(channel_name)
            table.add_row(
                channel_name,
                config.config.name,
                config.config.channel_type.replace("_", " ").title(),
                config.config.handle,
                f"{config.config.video.aspect_ratio} ({config.config.content.format})",
            )
        except Exception as e:
            logger.error(f"Error loading {channel_name}: {e}")
            table.add_row(
                channel_name,
                "[red]ERROR[/red]",
                "[red]Invalid config[/red]",
                "-",
                "-",
            )

    console.print(table)
    console.print()


@cli.command()
@click.option(
    "--subreddit",
    "-s",
    default=None,
    help="Subreddit to scrape (default: from .env)",
)
@click.option(
    "--limit",
    "-l",
    default=25,
    type=int,
    help="Number of stories to fetch",
)
def update_stories(subreddit: str | None, limit: int):
    """Download stories from Reddit and save to Google Sheets."""

    async def run():
        orchestrator = WorkflowOrchestrator()
        try:
            await orchestrator.update_stories_from_reddit(subreddit=subreddit, limit=limit)
        finally:
            await orchestrator.close()

    asyncio.run(run())


@cli.command()
@click.option(
    "--count",
    "-c",
    default=1,
    type=int,
    help="Number of videos to generate",
)
@click.option(
    "--update/--no-update",
    default=False,
    help="Update stories from Reddit first",
)
@click.option(
    "--profile",
    "-p",
    default=None,
    help="Voice/music profile to use (default: from profiles.yaml)",
)
def generate(count: int, update: bool, profile: str | None):
    """Generate videos from stories in Google Sheets."""

    async def run():
        orchestrator = WorkflowOrchestrator(profile=profile)
        try:
            await orchestrator.run_complete_workflow(
                update_stories=update,
                process_count=count,
            )
        finally:
            await orchestrator.close()

    asyncio.run(run())


@cli.command()
@click.argument("story_id")
@click.option(
    "--profile",
    "-p",
    default=None,
    help="Voice/music profile to use (default: from profiles.yaml)",
)
def generate_single(story_id: str, profile: str | None):
    """
    Generate video from a single Reddit story by ID.

    STORY_ID is the Reddit post ID (e.g., 'abc123')
    """

    async def run():
        orchestrator = WorkflowOrchestrator(profile=profile)
        try:
            await orchestrator.run_single_story(story_id)
        finally:
            await orchestrator.close()

    asyncio.run(run())


@cli.command()
def check_server():
    """Check if the media processing server is running."""

    async def run():
        from src.services.media import MediaService

        media = MediaService()
        try:
            await media.health_check()
            console.print("[bold green]✓ Media server is ready![/bold green]")
        except Exception as e:
            console.print(f"[bold red]✗ Media server check failed: {e}[/bold red]")
            sys.exit(1)
        finally:
            await media.close()

    asyncio.run(run())


@cli.command()
def validate_config():
    """Validate configuration and environment variables."""
    from src.config import settings

    console.print("\n[bold cyan]Configuration Validation[/bold cyan]\n")

    errors = []
    warnings = []

    # Check required API keys
    if not settings.google_api_key:
        errors.append("GOOGLE_API_KEY is missing")
    else:
        console.print("[green]✓[/green] Google API Key configured")

    if not settings.together_api_key:
        errors.append("TOGETHER_API_KEY is missing")
    else:
        console.print("[green]✓[/green] Together.ai API Key configured")

    # Check Google credentials file
    if not settings.google_credentials_path.exists():
        errors.append(f"Google credentials file not found: {settings.google_credentials_path}")
    else:
        console.print(f"[green]✓[/green] Google credentials file found")

    # Check optional settings
    if not settings.background_music_id:
        warnings.append("Background music not configured (optional)")

    if settings.tts_engine == "chatterbox" and not settings.chatterbox_voice_sample_id:
        warnings.append("Chatterbox voice sample not configured (using default voice)")

    # Print results
    if errors:
        console.print("\n[bold red]❌ Errors:[/bold red]")
        for error in errors:
            console.print(f"  • {error}")

    if warnings:
        console.print("\n[yellow]⚠ Warnings:[/yellow]")
        for warning in warnings:
            console.print(f"  • {warning}")

    if not errors:
        console.print("\n[bold green]✓ Configuration is valid![/bold green]\n")
    else:
        console.print(
            "\n[bold red]Please fix the errors above before running the workflow.[/bold red]\n"
        )
        sys.exit(1)


@cli.command()
def init():
    """Initialize project: create .env from template."""
    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        console.print("[yellow]⚠ .env file already exists[/yellow]")
        if not click.confirm("Overwrite?"):
            return

    if not env_example.exists():
        console.print("[red]✗ .env.example not found[/red]")
        return

    env_file.write_text(env_example.read_text())
    console.print("[green]✓ Created .env file[/green]")
    console.print("\n[cyan]Next steps:[/cyan]")
    console.print("1. Edit .env and add your API keys")
    console.print("2. Place your Google credentials.json in the project root")
    console.print("3. Run: python -m src.main validate-config")
    console.print("4. Run: python -m src.main check-server")
    console.print("5. Run: python -m src.main generate --count 1\n")


@cli.command()
@click.option(
    "--limit",
    "-l",
    default=20,
    type=int,
    help="Maximum number of videos to upload (default: 20, YouTube API daily limit)",
)
def batch_upload(limit: int):
    """
    Phase 1: Upload videos to YouTube as PRIVATE with temporary metadata.

    Uploads all video files in output/ directory to YouTube as private videos
    with temporary metadata. Video IDs are saved to output/video_ids.csv for
    later scheduling.

    This is the first phase of the 2-phase upload/schedule system.
    After uploading, use 'batch-schedule' to set final metadata and publish times.

    Examples:
        # Upload all videos (max 20 per day)
        python -m src.main batch-upload

        # Upload only 5 videos
        python -m src.main batch-upload --limit 5
    """
    import csv
    from src.services.youtube import YouTubeService

    async def run():
        console.print("\n[bold cyan]📤 Phase 1: Batch Upload (Private)[/bold cyan]\n")

        output_dir = Path("./output")
        if not output_dir.exists():
            console.print("[red]✗ Output directory not found[/red]")
            return

        # Find all video files
        video_files = sorted(output_dir.glob("video_*.mp4"))
        if not video_files:
            console.print("[yellow]⚠ No videos found in output/[/yellow]")
            return

        # Limit to avoid API quota issues
        if len(video_files) > limit:
            console.print(f"[yellow]⚠ Found {len(video_files)} videos, limiting to {limit} (API limit)[/yellow]")
            video_files = video_files[:limit]

        console.print(f"Found {len(video_files)} videos to upload\n")

        # Initialize YouTube service
        youtube = YouTubeService()

        # Upload videos and collect video IDs
        uploaded_videos = []
        failed_videos = []

        for i, video_file in enumerate(video_files, 1):
            console.print(f"[cyan]Uploading {i}/{len(video_files)}: {video_file.name}[/cyan]")

            try:
                result = youtube.upload_video_as_private(
                    video_path=video_file,
                    filename=video_file.name,
                )
                uploaded_videos.append((video_file.name, result.video_id))
                console.print(f"[green]✓ Uploaded: {result.video_id}[/green]\n")

            except Exception as e:
                logger.exception(f"Failed to upload {video_file.name}")
                console.print(f"[red]✗ Failed: {e}[/red]\n")
                failed_videos.append(video_file.name)

        # Save video IDs to CSV
        if uploaded_videos:
            csv_path = output_dir / "video_ids.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["filename", "video_id"])
                writer.writerows(uploaded_videos)

            console.print(f"[green]✓ Saved {len(uploaded_videos)} video IDs to {csv_path}[/green]\n")

        # Summary
        console.print("[bold cyan]Upload Summary:[/bold cyan]")
        console.print(f"  ✓ Uploaded: {len(uploaded_videos)}")
        console.print(f"  ✗ Failed: {len(failed_videos)}")

        if uploaded_videos:
            console.print("\n[bold green]Next step:[/bold green]")
            console.print("  Run: python -m src.main batch-schedule")
            console.print("  This will set final metadata and schedule publish times.\n")

    asyncio.run(run())


@cli.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview schedule without updating videos",
)
def batch_schedule(dry_run: bool):
    """
    Phase 2: Schedule uploaded videos with final metadata and publish times.

    Reads video_ids.csv and metadata JSON files, calculates optimal publish
    schedule (filling gaps in existing schedule), and updates videos with
    final metadata and scheduled publish times.

    This is the second phase of the 2-phase upload/schedule system.
    Videos must be uploaded first using 'batch-upload'.

    The scheduler will:
    - Check for existing scheduled videos on YouTube
    - Fill gaps in the schedule (6 AM - 4 PM, every 2 hours)
    - If today is full, start tomorrow at 6 AM
    - Update videos with SEO-optimized metadata

    Examples:
        # Preview schedule
        python -m src.main batch-schedule --dry-run

        # Schedule videos
        python -m src.main batch-schedule
    """
    import csv
    import json
    from src.services.youtube import YouTubeService
    from src.services.scheduler import VideoScheduler
    from rich.table import Table

    async def run():
        console.print("\n[bold cyan]📅 Phase 2: Batch Schedule[/bold cyan]\n")

        output_dir = Path("./output")
        csv_path = output_dir / "video_ids.csv"

        if not csv_path.exists():
            console.print("[red]✗ video_ids.csv not found[/red]")
            console.print("[yellow]Run 'batch-upload' first to upload videos[/yellow]")
            return

        # Read video IDs
        video_data = []
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            video_data = list(reader)

        if not video_data:
            console.print("[yellow]⚠ No videos in video_ids.csv[/yellow]")
            return

        console.print(f"Found {len(video_data)} uploaded videos\n")

        # Initialize services
        youtube = YouTubeService()
        scheduler = VideoScheduler()

        # Get existing scheduled videos from YouTube
        console.print("[cyan]Checking existing scheduled videos on YouTube...[/cyan]")
        existing_videos = youtube.get_scheduled_videos()
        console.print(f"Found {len(existing_videos)} already scheduled videos\n")

        # Calculate schedule for new videos
        publish_times = []
        for i, video in enumerate(video_data):
            # Calculate next available slot based on existing schedule + already calculated
            all_scheduled = existing_videos + [{"publishAt": pt.strftime("%Y-%m-%dT%H:%M:%S.000Z")} for pt in publish_times]
            next_slot = scheduler.calculate_next_available_slot(all_scheduled)
            publish_times.append(next_slot)

        # Display schedule
        table = Table(title="Scheduled Videos" + (" (DRY RUN)" if dry_run else ""))
        table.add_column("Video", style="cyan")
        table.add_column("Video ID", style="yellow")
        table.add_column("Publish Time (Local)", style="green")
        table.add_column("Publish Time (UTC)", style="blue")

        for video, publish_time in zip(video_data, publish_times):
            publish_local = publish_time.astimezone(scheduler.timezone)
            table.add_row(
                video["filename"],
                video["video_id"],
                publish_local.strftime("%Y-%m-%d %H:%M"),
                publish_time.strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)
        console.print()

        if dry_run:
            console.print("[yellow]🔍 Dry run mode - no videos will be updated[/yellow]\n")
            return

        # Update videos with metadata and schedule
        console.print("[bold cyan]Updating videos with metadata and schedule...[/bold cyan]\n")

        updated_count = 0
        failed_count = 0

        for video, publish_time in zip(video_data, publish_times):
            filename = video["filename"]
            video_id = video["video_id"]

            console.print(f"[cyan]Scheduling {filename} ({video_id})...[/cyan]")

            try:
                # Load metadata if exists
                metadata_file = filename.replace(".mp4", "_metadata.json")
                metadata_path = output_dir / metadata_file

                if metadata_path.exists():
                    with open(metadata_path, encoding="utf-8") as f:
                        metadata = json.load(f)
                        title = metadata.get("title", "Untitled Video")
                        description = metadata.get("description", "")
                        tags = metadata.get("tags", [])
                        category_id = metadata.get("category_id", settings.youtube_category_id)
                else:
                    # Use defaults
                    logger.warning(f"No metadata found for {filename}, using defaults")
                    title = f"Video {video_id}"
                    description = "Motivational content. #motivation #shorts"
                    tags = ["motivation", "shorts"]
                    category_id = settings.youtube_category_id

                # Update video with schedule
                youtube.update_video_schedule(
                    video_id=video_id,
                    title=title,
                    description=description,
                    tags=tags,
                    category_id=category_id,
                    publish_at=publish_time,
                )

                publish_local = publish_time.astimezone(scheduler.timezone)
                console.print(f"[green]✓ Scheduled for {publish_local.strftime('%Y-%m-%d %H:%M')}[/green]\n")
                updated_count += 1

            except Exception as e:
                logger.exception(f"Failed to schedule {filename}")
                console.print(f"[red]✗ Failed: {e}[/red]\n")
                failed_count += 1

        # Summary
        console.print("[bold cyan]Schedule Summary:[/bold cyan]")
        console.print(f"  ✓ Scheduled: {updated_count}")
        console.print(f"  ✗ Failed: {failed_count}\n")

        if updated_count > 0:
            console.print("[bold green]Done![/bold green]")
            console.print("Check YouTube Studio to verify scheduled videos.\n")

    asyncio.run(run())


@cli.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Calculate schedule but don't upload (preview only)",
)
@click.option(
    "--start-date",
    default=None,
    help="Start date for scheduling (YYYY-MM-DD, default: tomorrow)",
)
def schedule_uploads(dry_run: bool, start_date: str | None):
    """
    Schedule batch upload of all videos in output/ directory.

    Uploads all videos with automatic scheduling:
    - Daily: 6 AM, 8 AM, 10 AM, 12 PM, 2 PM, 4 PM (6 videos/day)
    - Videos uploaded as private with scheduled publish times
    - Uses SEO metadata from JSON files if available

    Examples:
        # Preview schedule without uploading
        python -m src.main schedule-uploads --dry-run

        # Upload and schedule starting tomorrow
        python -m src.main schedule-uploads

        # Upload and schedule starting specific date
        python -m src.main schedule-uploads --start-date 2025-11-15
    """
    from datetime import datetime

    async def run():
        orchestrator = WorkflowOrchestrator()
        try:
            # Parse start date if provided
            start_datetime = None
            if start_date:
                try:
                    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                    console.print(f"[cyan]Starting schedule from: {start_date}[/cyan]\n")
                except ValueError:
                    console.print("[red]✗ Invalid date format. Use YYYY-MM-DD[/red]")
                    return

            # Run batch scheduling
            results = await orchestrator.schedule_batch_upload(
                start_date=start_datetime,
                dry_run=dry_run,
            )

            if results and not dry_run:
                # Save results to CSV for reference
                import csv
                output_file = Path("output/scheduled_videos.csv")
                with open(output_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Video Path", "Publish Time (UTC)", "YouTube URL"])
                    for video_path, publish_time, url in results:
                        writer.writerow([video_path, publish_time.isoformat(), url])

                console.print(f"[green]✓ Schedule saved to {output_file}[/green]\n")

        finally:
            await orchestrator.close()

    asyncio.run(run())


if __name__ == "__main__":
    cli()

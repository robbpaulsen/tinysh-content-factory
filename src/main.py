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

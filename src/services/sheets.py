"""Google Sheets service for story management."""

import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models import RedditPost, StoryRecord

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetsService:
    """Service for managing stories in Google Sheets."""

    def __init__(self, credentials_path: Path | None = None, sheet_name: str | None = None):
        """
        Initialize Google Sheets service.

        Args:
            credentials_path: Path to OAuth credentials JSON
            sheet_name: Custom sheet tab name (default: from settings.sheet_name)
        """
        self.credentials_path = credentials_path or settings.google_credentials_path
        self.spreadsheet_id = settings.google_sheet_id
        self.sheet_name = sheet_name or settings.sheet_name
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        creds = None
        token_path = Path("token.json")

        # Load existing token
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Google credentials")
                creds.refresh(Request())
            else:
                logger.info("Starting OAuth flow for Google Sheets")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                # Force account selection to avoid browser cache issues
                creds = flow.run_local_server(port=0, prompt="consent")

            # Save credentials for next run
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        self.service = build("sheets", "v4", credentials=creds)
        logger.info("Google Sheets authentication successful")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def save_stories(self, posts: list[RedditPost]) -> int:
        """
        Save Reddit posts to Google Sheets.

        Args:
            posts: List of RedditPost objects

        Returns:
            Number of stories saved
        """
        logger.info(f"Saving {len(posts)} stories to Google Sheets")

        # Prepare rows
        rows = []
        for post in posts:
            rows.append([
                post.id,
                post.title,
                post.content,
                "",  # video_id placeholder
            ])

        # Append to sheet
        range_name = f"{self.sheet_name}!A:D"
        body = {"values": rows}

        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body=body,
        ).execute()

        logger.info(f"Successfully saved {len(posts)} stories")
        return len(posts)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def get_story_without_video(self) -> StoryRecord | None:
        """
        Get one story from the sheet that doesn't have a video_id yet.

        Returns:
            StoryRecord or None if no unprocessed story found
        """
        logger.info("Fetching story without video from Google Sheets")

        # Get all rows
        range_name = f"{self.sheet_name}!A:D"
        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=range_name)
            .execute()
        )

        rows = result.get("values", [])

        # Find first row without video_id (column D empty or missing)
        for idx, row in enumerate(rows, start=1):
            # Skip if less than 3 columns (need id, title, content at minimum)
            if len(row) < 3:
                continue

            post_id, title, content = row[0], row[1], row[2]
            video_id = row[3] if len(row) > 3 else ""

            # Check if video_id is empty
            if not video_id or video_id.strip() == "":
                logger.info(f"Found unprocessed story: {post_id} (row {idx})")
                return StoryRecord(
                    id=post_id,
                    title=title,
                    content=content,
                    video_id=None,
                    row_number=idx,
                )

        logger.info("No unprocessed stories found")
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def update_video_id(self, row_number: int, video_id: str):
        """
        Update the video_id for a story in the sheet.

        Args:
            row_number: Row number (1-indexed)
            video_id: Video file ID to set
        """
        logger.info(f"Updating row {row_number} with video_id: {video_id}")

        range_name = f"{self.sheet_name}!D{row_number}"
        body = {"values": [[video_id]]}

        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body=body,
        ).execute()

        logger.info(f"Successfully updated row {row_number}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def get_all_stories(self) -> list[StoryRecord]:
        """
        Get all stories from the sheet.

        Returns:
            List of StoryRecord objects
        """
        logger.info("Fetching all stories from Google Sheets")

        range_name = f"{self.sheet_name}!A:D"
        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=range_name)
            .execute()
        )

        rows = result.get("values", [])
        stories = []

        for idx, row in enumerate(rows, start=1):
            if len(row) < 3:
                continue

            post_id, title, content = row[0], row[1], row[2]
            video_id = row[3] if len(row) > 3 and row[3].strip() else None

            stories.append(
                StoryRecord(
                    id=post_id,
                    title=title,
                    content=content,
                    video_id=video_id,
                    row_number=idx,
                )
            )

        logger.info(f"Retrieved {len(stories)} stories")
        return stories

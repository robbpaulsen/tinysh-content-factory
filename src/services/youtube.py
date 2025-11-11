"""YouTube service for video uploads."""

import logging
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models import YouTubeUploadResult

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubeService:
    """Service for uploading videos to YouTube."""

    def __init__(self, credentials_path: Path | None = None):
        """
        Initialize YouTube service.

        Args:
            credentials_path: Path to OAuth credentials JSON
        """
        self.credentials_path = credentials_path or settings.google_credentials_path
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with YouTube API."""
        creds = None
        token_path = Path("token_youtube.json")

        # Load existing token
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing YouTube credentials")
                creds.refresh(Request())
            else:
                logger.info("Starting OAuth flow for YouTube")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        self.service = build("youtube", "v3", credentials=creds)
        logger.info("YouTube authentication successful")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=30),
        reraise=True,
    )
    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str] | None = None,
        category_id: str | None = None,
        privacy_status: str | None = None,
        publish_at: datetime | None = None,
    ) -> YouTubeUploadResult:
        """
        Upload a video to YouTube.

        Args:
            video_path: Path to video file
            title: Video title (max 100 chars)
            description: Video description (max 5000 chars)
            tags: List of tags (optional)
            category_id: YouTube category ID (optional, defaults to settings)
            privacy_status: Privacy status (optional, defaults to settings)
            publish_at: Scheduled publish time (optional, requires privacy="private")

        Returns:
            YouTubeUploadResult with video ID and URL

        Note:
            If publish_at is set, video will be uploaded as private and scheduled.
            YouTube requires RFC 3339 format: YYYY-MM-DDTHH:MM:SS.sZ
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Truncate title and description to YouTube limits
        title = title[:100]
        description = description[:5000]
        tags = tags or []
        category_id = category_id or settings.youtube_category_id
        privacy_status = privacy_status or settings.youtube_privacy_status

        logger.info(f"Uploading video to YouTube: {title}")
        logger.info(f"Privacy: {privacy_status}, Category: {category_id}")

        # Validate scheduling requirements
        if publish_at and privacy_status != "private":
            logger.warning(
                "Scheduled videos must be private. Forcing privacy_status='private'"
            )
            privacy_status = "private"

        # Prepare request body
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
                # containsSyntheticMedia: Only TRUE if imitating/impersonating real people
                # FALSE for generic AI-generated content (images, text, synthetic voices)
                # Setting TRUE severely limits reach and monetization
            },
        }

        # Add scheduled publish time if provided
        if publish_at:
            # Convert to RFC 3339 format required by YouTube
            publish_time_str = publish_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            body["status"]["publishAt"] = publish_time_str
            logger.info(f"Video scheduled for: {publish_time_str}")

        # Create media upload
        media = MediaFileUpload(
            str(video_path),
            chunksize=-1,  # Upload in a single request
            resumable=True,
        )

        # Execute upload
        request = self.service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info(f"Upload progress: {progress}%")

        video_id = response["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        logger.info(f"Video uploaded successfully: {video_url}")

        return YouTubeUploadResult(
            video_id=video_id,
            url=video_url,
            title=title,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def update_video_metadata(
        self,
        video_id: str,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ):
        """
        Update metadata for an existing video.

        Args:
            video_id: YouTube video ID
            title: New title (optional)
            description: New description (optional)
            tags: New tags (optional)
        """
        logger.info(f"Updating metadata for video: {video_id}")

        # Get current video details
        response = self.service.videos().list(part="snippet", id=video_id).execute()

        if not response["items"]:
            raise ValueError(f"Video not found: {video_id}")

        video = response["items"][0]
        snippet = video["snippet"]

        # Update fields if provided
        if title:
            snippet["title"] = title[:100]
        if description:
            snippet["description"] = description[:5000]
        if tags:
            snippet["tags"] = tags

        # Update video
        self.service.videos().update(
            part="snippet",
            body={"id": video_id, "snippet": snippet},
        ).execute()

        logger.info(f"Video metadata updated: {video_id}")

    def delete_video(self, video_id: str):
        """
        Delete a video from YouTube.

        Args:
            video_id: YouTube video ID
        """
        logger.info(f"Deleting video: {video_id}")

        self.service.videos().delete(id=video_id).execute()

        logger.info(f"Video deleted: {video_id}")

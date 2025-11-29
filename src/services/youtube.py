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

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
]


class YouTubeService:
    """Service for uploading videos to YouTube."""

    def __init__(self, credentials_path: Path | None = None, token_path: Path | None = None):
        """
        Initialize YouTube service.

        Args:
            credentials_path: Path to OAuth credentials JSON
            token_path: Path to save/load token (default: token_youtube.json in same dir as credentials)
        """
        self.credentials_path = credentials_path or settings.google_credentials_path

        # Determine token path: same directory as credentials, or custom path
        if token_path:
            self.token_path = token_path
        elif credentials_path:
            # Save token next to credentials file
            self.token_path = credentials_path.parent / "token_youtube.json"
        else:
            # Default: root directory
            self.token_path = Path("token_youtube.json")

        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with YouTube API."""
        creds = None

        # Load existing token
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing YouTube credentials")
                creds.refresh(Request())
            else:
                logger.info(
                    f"Starting OAuth flow for YouTube (credentials: {self.credentials_path})"
                )
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), SCOPES)
                # Force account selection to avoid browser cache issues
                creds = flow.run_local_server(port=0, prompt="consent")

            # Save credentials for next run
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
            logger.info(f"Token saved to: {self.token_path}")

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
            logger.warning("Scheduled videos must be private. Forcing privacy_status='private'")
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=30),
        reraise=True,
    )
    def upload_video_as_private(
        self,
        video_path: Path,
        filename: str,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        category_id: str | None = None,
        made_for_kids: bool = False,
        default_language: str | None = None,
    ) -> YouTubeUploadResult:
        """
        Upload a video to YouTube as PRIVATE.

        This is Phase 1 of the 2-phase upload/schedule system.
        Can optionally include final metadata during upload to ensure
        video is ready even before scheduling.

        Args:
            video_path: Path to video file
            filename: Original filename for tracking
            title: Video title (optional)
            description: Video description (optional)
            tags: List of tags (optional)
            category_id: YouTube category ID (optional)
            made_for_kids: Self-declared made for kids status (default: False)
            default_language: Default language of video (e.g. 'en', 'es')

        Returns:
            YouTubeUploadResult with video ID and URL
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Use provided metadata or fallbacks
        final_title = title or "Uploading... (metadata pending)"
        final_description = description or "This video is being processed. Metadata will be updated shortly."
        final_tags = tags or []
        final_category_id = category_id or settings.youtube_category_id

        # Truncate to limits just in case
        final_title = final_title[:100]
        final_description = final_description[:5000]

        logger.info(f"Uploading video as private: {filename}")
        if title:
            logger.info(f"Using provided metadata - Title: {final_title}")

        # Prepare request body
        body = {
            "snippet": {
                "title": final_title,
                "description": final_description,
                "tags": final_tags,
                "categoryId": final_category_id,
            },
            "status": {
                "privacyStatus": "private",
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }

        # Add optional snippet fields
        if default_language:
            body["snippet"]["defaultLanguage"] = default_language
            # Also set defaultAudioLanguage if it matches defaultLanguage
            body["snippet"]["defaultAudioLanguage"] = default_language

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

        logger.info(f"Video uploaded successfully (private): {video_url}")

        return YouTubeUploadResult(
            video_id=video_id,
            url=video_url,
            title=final_title,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def update_video_schedule(
        self,
        video_id: str,
        title: str,
        description: str,
        tags: list[str],
        category_id: str,
        publish_at: datetime,
    ):
        """
        Update video with final metadata and schedule for publication.

        This is Phase 2 of the 2-phase upload/schedule system.
        Updates an already uploaded private video with final metadata
        and sets the scheduled publish time.

        Args:
            video_id: YouTube video ID
            title: Final video title
            description: Final video description
            tags: List of tags
            category_id: YouTube category ID
            publish_at: Scheduled publish time (UTC)
        """
        logger.info(f"Scheduling video {video_id} for {publish_at.strftime('%Y-%m-%d %H:%M UTC')}")

        # Truncate to YouTube limits
        title = title[:100]
        description = description[:5000]

        # Convert to RFC 3339 format
        publish_time_str = publish_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # Prepare update body
        body = {
            "id": video_id,
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": "private",
                "publishAt": publish_time_str,
                "selfDeclaredMadeForKids": False,
            },
        }

        # Execute update
        self.service.videos().update(
            part="snippet,status",
            body=body,
        ).execute()

        logger.info(f"Video {video_id} scheduled successfully for {publish_time_str}")

    def get_scheduled_videos(self, max_results: int = 50) -> list[dict]:
        """
        Get all scheduled videos from the authenticated channel.

        Returns videos that are private with a publishAt time set.
        Used to determine the next available time slot.

        Args:
            max_results: Maximum number of videos to fetch (default: 50)

        Returns:
            List of video dictionaries with id, publishAt, and snippet info
        """
        logger.info("Fetching scheduled videos from channel")

        try:
            # 1. Get channel's "uploads" playlist ID
            channels_response = (
                self.service.channels()
                .list(
                    part="contentDetails",
                    mine=True,
                )
                .execute()
            )

            if not channels_response.get("items"):
                logger.warning("No channel found for authenticated user")
                return []

            uploads_playlist_id = channels_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            logger.debug(f"Found uploads playlist ID: {uploads_playlist_id}")

            # 2. Get videos from the "uploads" playlist
            # playlistItems gives us the video IDs
            playlist_response = (
                self.service.playlistItems()
                .list(
                    part="snippet",
                    playlistId=uploads_playlist_id,
                    maxResults=max_results,
                )
                .execute()
            )

            if not playlist_response.get("items"):
                logger.info("No videos found in uploads playlist")
                return []

            # Extract video IDs
            video_ids = []
            for item in playlist_response["items"]:
                video_ids.append(item["snippet"]["resourceId"]["videoId"])

            if not video_ids:
                return []

            # 3. Get full details (status) for these videos
            # We need this because playlistItems doesn't always have accurate status/publishAt
            videos_response = (
                self.service.videos()
                .list(
                    part="snippet,status",
                    id=",".join(video_ids),
                )
                .execute()
            )

            scheduled_videos = []
            for video in videos_response.get("items", []):
                status = video.get("status", {})

                # Check if video is private and has publishAt set
                if status.get("privacyStatus") == "private" and status.get("publishAt"):
                    scheduled_videos.append(
                        {
                            "id": video["id"],
                            "title": video["snippet"]["title"],
                            "publishAt": status["publishAt"],
                        }
                    )

            logger.info(f"Found {len(scheduled_videos)} scheduled videos")
            return scheduled_videos

        except Exception as e:
            logger.error(f"Error fetching scheduled videos: {e}")
            return []

"""Data models for the workflow."""

from pydantic import BaseModel, Field


class RedditPost(BaseModel):
    """Reddit post data."""

    id: str = Field(..., description="Reddit post ID")
    title: str = Field(..., description="Post title")
    content: str = Field(..., description="Post selftext content")
    subreddit: str = Field(..., description="Subreddit name")
    score: int = Field(default=0, description="Post score/upvotes")
    url: str = Field(..., description="Reddit post URL")


class Scene(BaseModel):
    """A scene in the video with text and image prompt."""

    text: str = Field(..., description="Text to be spoken in this scene")
    image_prompt: str = Field(..., description="Prompt for image generation")


class VideoScript(BaseModel):
    """Complete video script with metadata."""

    scenes: list[Scene] = Field(..., description="List of scenes")
    title: str = Field(..., description="Video title")
    description: str = Field(..., description="Video description")


class GeneratedImage(BaseModel):
    """Generated image data."""

    url: str = Field(..., description="Image URL from Together.ai")
    file_id: str = Field(..., description="File ID after upload to media server")


class GeneratedTTS(BaseModel):
    """Generated TTS audio data."""

    file_id: str = Field(..., description="TTS audio file ID")
    duration: float | None = Field(default=None, description="Audio duration in seconds")


class GeneratedVideo(BaseModel):
    """Generated video clip with captions."""

    file_id: str = Field(..., description="Video file ID")
    tts_id: str = Field(..., description="TTS audio file ID")
    image_id: str = Field(..., description="Background image file ID")


class MediaProcessingStatus(BaseModel):
    """Status response from media server."""

    status: str = Field(..., description="Processing status: ready, processing, not_found, failed")
    file_id: str | None = Field(default=None, description="File ID if available")
    url: str | None = Field(default=None, description="Download URL if ready")
    error: str | None = Field(default=None, description="Error message if failed")


class StoryRecord(BaseModel):
    """Story record in Google Sheets."""

    id: str = Field(..., description="Reddit post ID")
    title: str = Field(..., description="Story title")
    content: str = Field(..., description="Story content")
    video_id: str | None = Field(default=None, description="Generated video file ID")
    row_number: int | None = Field(default=None, description="Row number in sheet")


class YouTubeUploadResult(BaseModel):
    """Result of YouTube video upload."""

    video_id: str = Field(..., description="YouTube video ID")
    url: str = Field(..., description="YouTube video URL")
    title: str = Field(..., description="Video title")


class SEOMetadata(BaseModel):
    """SEO-optimized metadata for YouTube videos."""

    title: str = Field(..., description="SEO-optimized video title (max 60 chars)")
    description: str = Field(..., description="SEO-optimized video description with hashtags")
    tags: list[str] = Field(..., description="List of relevant tags (10-15 recommended)")
    category_id: str = Field(default="22", description="YouTube category ID")

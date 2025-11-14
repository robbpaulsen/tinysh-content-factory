"""LLM service using Google Gemini."""

import asyncio
import json
import logging
import re
from functools import wraps

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models import Scene, VideoScript
from src.services.logger_service import log_api_call

logger = logging.getLogger(__name__)


def async_retry(func):
    """Wrapper to make sync Gemini calls work with async code."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Run sync Gemini call in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    return wrapper


class LLMService:
    """Service for generating content using Google Gemini."""

    def __init__(self, channel_config: "ChannelConfig | None" = None):
        """
        Initialize Gemini API client.

        Args:
            channel_config: Optional channel configuration for custom prompts
        """
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        self.channel_config = channel_config

        # Load custom prompts if channel config provided
        self.custom_script_prompt = None
        self.custom_image_prompt = None

        if self.channel_config:
            self.custom_script_prompt = self.channel_config.get_prompt('script')
            self.custom_image_prompt = self.channel_config.get_prompt('image')

            if self.custom_script_prompt:
                logger.info(f"✓ Loaded custom SCRIPT prompt for {self.channel_config.config.name}")
            if self.custom_image_prompt:
                logger.info(f"✓ Loaded custom IMAGE prompt for {self.channel_config.config.name}")

        logger.info("Initialized Gemini LLM service")

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Remove <think> tags and extra whitespace from text.

        Args:
            text: Input text with potential tags

        Returns:
            Cleaned text
        """
        # Remove <think>...</think> blocks
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _generate_motivational_speech_sync(
        self, story_title: str, story_content: str, content_type: str
    ) -> str:
        """Synchronous version of speech generation (for thread pool)."""
        logger.info(f"Generating {content_type} from story: {story_title[:50]}...")
        log_api_call("Gemini", "generate_motivational_speech", "starting", logger=logger)

        prompt = f"""Based on the following Reddit story, create a compelling {content_type}.

Story Title: {story_title}

Story Content:
{story_content}

Instructions:
- Extract the core lesson or message from this story
- Create an inspiring, motivational narrative
- TARGET LENGTH: 15-45 seconds when spoken (480-1440 tokens)
- For YouTube Shorts: Keep between 15s minimum and 45s maximum
- Use powerful, emotional language
- Make it relatable and actionable
- Write in second person ("you") to engage the audience
- Do NOT include any <think> tags or meta-commentary

IMPORTANT: Stay within 480-1440 tokens (15-45 seconds). Gemini measures 32 tokens = 1 second of speech.

Generate only the motivational speech text, nothing else."""

        try:
            response = self.model.generate_content(prompt)
            speech = self._clean_text(response.text)

            log_api_call("Gemini", "generate_motivational_speech", "success",
                        details=f"{len(speech)} chars", logger=logger)
            logger.info(f"Generated speech ({len(speech)} chars)")
            return speech
        except Exception as e:
            log_api_call("Gemini", "generate_motivational_speech", "error",
                        details=str(e), logger=logger)
            raise

    async def create_motivational_speech(
        self, story_title: str, story_content: str, content_type: str | None = None
    ) -> str:
        """
        Create a motivational speech from a Reddit story.

        Args:
            story_title: Title of the story
            story_content: Content of the story
            content_type: Type of content (defaults to settings.content_type)

        Returns:
            Generated motivational speech text
        """
        content_type = content_type or settings.content_type
        # Run in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._generate_motivational_speech_sync,
            story_title,
            story_content,
            content_type,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _generate_video_script_sync(self, motivational_text: str, art_style: str, story_title: str = "", story_content: str = "") -> VideoScript:
        """Synchronous version of script generation (for thread pool)."""
        logger.info("Creating video script with scenes and image prompts")
        log_api_call("Gemini", "generate_video_script", "starting", logger=logger)

        # Use custom script prompt if available
        if self.custom_script_prompt:
            logger.info("Using CUSTOM script prompt from channel")
            prompt = self.custom_script_prompt.format(title=story_title, content=story_content)
        else:
            logger.info("Using DEFAULT script prompt")
            prompt = f"""You are a video script creator for YouTube Shorts (15-45 seconds). Given a motivational speech, break it into 5-8 scenes.

Motivational Speech:
{motivational_text}

Art Style Context:
{art_style}

DURATION REQUIREMENTS:
- Total video: 15-45 seconds (Shorts format)
- Each scene: 2-6 seconds of speech
- Total speech should match motivational text length
- Gemini token count: 32 tokens = 1 second

MANDATORY SCRIPT STRUCTURE:
The script must adopt a friendly, energetic, and engaging tone suitable for YouTube. The final script must follow this structure:

1. [OPENING HOOK]: A brief (max 5 seconds) energetic welcome and introduction to the video's main topic.
2. [MAIN CONTENT]: The 10-45s content based on the provided material.
3. [CLOSING CTA]: A clear, conversational Call-to-Action that explicitly mentions "MommentumMindset" and encourages the viewer to subscribe, like the video, and leave a comment.

For each scene:
1. Provide the exact text to be spoken (2-3 sentences max, ~64-192 tokens per scene)
2. Create a detailed image generation prompt that:
   - Captures the emotion/message of that text
   - Follows the art style provided above
   - Uses cinematic, photographic descriptions
   - Is specific and visual (not abstract)

Also provide:
- A catchy video title (under 60 characters)
- A video description (2-3 sentences)

Return your response as a JSON object with this exact structure:
{{
  "title": "Video Title Here",
  "description": "Video description here",
  "scenes": [
    {{
      "text": "First scene text to be spoken",
      "image_prompt": "Detailed image prompt for this scene"
    }},
    {{
      "text": "Second scene text",
      "image_prompt": "Another detailed image prompt"
    }}
  ]
}}

IMPORTANT: Return ONLY valid JSON, no other text or markdown formatting."""

        try:
            response = self.model.generate_content(prompt)
            response_text = self._clean_text(response.text)

            # Extract JSON from markdown code blocks if present
            json_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)

            # Parse JSON response
            try:
                data = json.loads(response_text)
                script = VideoScript(
                    title=data["title"],
                    description=data["description"],
                    scenes=[Scene(**scene) for scene in data["scenes"]],
                )
                log_api_call("Gemini", "generate_video_script", "success",
                            details=f"{len(script.scenes)} scenes", logger=logger)
                logger.info(f"Created script with {len(script.scenes)} scenes")
                return script
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.debug(f"Raw response: {response_text[:500]}")
                log_api_call("Gemini", "generate_video_script", "error",
                            details=f"JSON parse error: {e}", logger=logger)
                raise ValueError(f"Invalid JSON response from LLM: {e}") from e
        except Exception as e:
            if not isinstance(e, ValueError):  # Don't double-log JSON errors
                log_api_call("Gemini", "generate_video_script", "error",
                            details=str(e), logger=logger)
            raise

    async def create_video_script(
        self, motivational_text: str, art_style: str | None = None, story_title: str = "", story_content: str = ""
    ) -> VideoScript:
        """
        Create a structured video script with scenes and image prompts.

        Args:
            motivational_text: The motivational speech text
            art_style: Art style description (defaults to settings.art_style)
            story_title: Original story title (for custom prompts)
            story_content: Original story content (for custom prompts)

        Returns:
            VideoScript with scenes and metadata
        """
        art_style = art_style or settings.art_style
        # Run in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._generate_video_script_sync, motivational_text, art_style, story_title, story_content
        )

    async def create_complete_workflow(
        self, story_title: str, story_content: str
    ) -> VideoScript:
        """
        Complete workflow: story -> motivational speech -> video script.

        Args:
            story_title: Title of the story
            story_content: Content of the story

        Returns:
            VideoScript ready for video generation
        """
        logger.info("Starting complete LLM workflow")

        # Step 1: Create motivational speech (skip if using custom script prompt)
        if self.custom_script_prompt:
            logger.info("Using custom script prompt - skipping motivational speech generation")
            speech = ""  # Not used when custom prompt exists
        else:
            speech = await self.create_motivational_speech(story_title, story_content)

        # Step 2: Create video script (pass story info for custom prompts)
        script = await self.create_video_script(speech, story_title=story_title, story_content=story_content)

        logger.info("Complete LLM workflow finished")
        return script

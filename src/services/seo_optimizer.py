"""SEO optimization service using Google Gemini."""

import asyncio
import json
import logging
import re
from functools import wraps

import google.generativeai as genai

from src.config import settings
from src.models import SEOMetadata

logger = logging.getLogger(__name__)


class SEOOptimizerService:
    """Service for generating SEO-optimized metadata using Google Gemini."""

    def __init__(self):
        """Initialize Gemini API client."""
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("Initialized SEO Optimizer service")

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

    def _generate_seo_metadata_sync(
        self,
        video_title: str,
        video_description: str,
        script_text: str,
        profile_name: str,
    ) -> SEOMetadata:
        """
        Synchronous version of SEO metadata generation (for thread pool).

        Args:
            video_title: Original video title from script
            video_description: Original video description from script
            script_text: Full video script text
            profile_name: Active profile name for context

        Returns:
            SEO-optimized metadata
        """
        logger.info("Generating SEO-optimized metadata with Gemini")

        # Combine all scenes text for context
        prompt = f"""You are a YouTube SEO expert. Based on the following video content, generate optimized metadata for maximum discoverability and CTR (Click-Through Rate).

Video Title (original): {video_title}
Video Description (original): {video_description}

Full Video Script:
{script_text}

Content Profile: {profile_name}

Generate SEO-optimized metadata with the following requirements:

1. **TITLE** (50-60 characters):
   - Must be catchy, clickable, and emotionally engaging
   - Include power words (e.g., "Secret", "Why", "How", "Proven")
   - Front-load the most important keywords
   - Create curiosity or promise value
   - Keep under 60 characters (YouTube truncates longer titles in mobile)

2. **DESCRIPTION** (150-300 characters):
   - First 2-3 lines are critical (visible before "Show more")
   - Include primary keywords naturally
   - Add a strong CTA (Call-to-Action)
   - Mention the channel name "MomentumMindset"
   - Include relevant hashtags at the end (3-5 max)
   - Use line breaks for readability

3. **TAGS** (10-15 tags):
   - Mix of broad and specific tags
   - Include: content topic, niche keywords, channel branding
   - Use multi-word phrases (e.g., "personal growth tips")
   - Include variations (singular/plural, synonyms)
   - No special characters or excessive punctuation

4. **CATEGORY_ID**:
   - Choose the most appropriate YouTube category:
     - "22" = People & Blogs
     - "24" = Entertainment
     - "26" = Howto & Style
     - "27" = Education
     - "28" = Science & Technology

Return your response as a JSON object with this exact structure:
{{
  "title": "Optimized YouTube title here",
  "description": "Optimized description with line breaks\\n\\nInclude CTA and hashtags\\n\\n#motivation #shorts #growth",
  "tags": ["tag1", "tag2", "tag3", "..."],
  "category_id": "22"
}}

IMPORTANT:
- Return ONLY valid JSON, no other text or markdown formatting
- Title must be under 60 characters
- Description should be 150-300 characters
- Include 10-15 relevant tags
- Choose category_id as string from the list above"""

        response = self.model.generate_content(prompt)
        response_text = self._clean_text(response.text)

        # Extract JSON from markdown code blocks if present
        json_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)

        # Parse JSON response
        try:
            data = json.loads(response_text)

            # Validate title length
            if len(data["title"]) > 60:
                logger.warning(f"Title too long ({len(data['title'])} chars), truncating")
                data["title"] = data["title"][:57] + "..."

            metadata = SEOMetadata(
                title=data["title"],
                description=data["description"],
                tags=data["tags"],
                category_id=data.get("category_id", settings.youtube_category_id),
            )

            logger.info(f"Generated SEO metadata: {metadata.title[:50]}...")
            logger.info(f"  Tags: {len(metadata.tags)} tags")
            logger.info(f"  Category: {metadata.category_id}")

            return metadata

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse SEO metadata response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
            raise ValueError(f"Invalid JSON response from LLM: {e}") from e

    async def generate_seo_metadata(
        self,
        video_title: str,
        video_description: str,
        script_text: str,
        profile_name: str = "default",
    ) -> SEOMetadata:
        """
        Generate SEO-optimized metadata for a video.

        Args:
            video_title: Original video title from script
            video_description: Original video description from script
            script_text: Full video script text (all scenes combined)
            profile_name: Active profile name for context

        Returns:
            SEO-optimized metadata ready for YouTube upload
        """
        # Run in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._generate_seo_metadata_sync,
            video_title,
            video_description,
            script_text,
            profile_name,
        )

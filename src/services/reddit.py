"""Reddit service for scraping stories using public JSON endpoints."""

import logging
from datetime import datetime, timezone
from typing import Literal

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models import RedditPost

logger = logging.getLogger(__name__)


class RedditService:
    """Service for fetching Reddit posts via public JSON endpoints."""

    def __init__(self):
        """Initialize HTTP client for Reddit."""
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )

    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, "client"):
            self.client.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def get_top_stories(
        self,
        subreddit_name: str | None = None,
        time_filter: Literal["day", "week", "month", "year", "all"] = "month",
        limit: int = 25,
        min_content_length: int = 100,
        min_timestamp: float | None = None,
    ) -> list[RedditPost]:
        """
        Get top stories from a subreddit using public JSON endpoint.

        Args:
            subreddit_name: Subreddit name (defaults to settings.subreddit if not provided)
            time_filter: Time filter for top posts
            limit: Maximum number of posts to retrieve per request
            min_content_length: Minimum content length to filter
            min_timestamp: Filter posts created after this UTC timestamp

        Returns:
            List of RedditPost objects
        """
        if not subreddit_name:
            subreddit_name = settings.subreddit
            logger.warning(f"No subreddit provided, using default from .env: r/{subreddit_name}")

        logger.info(f"Fetching top {limit} stories from r/{subreddit_name} ({time_filter})")

        # Use Reddit's public JSON endpoint (same as n8n)
        url = f"https://www.reddit.com/r/{subreddit_name}/top.json"
        params = {"t": time_filter, "limit": min(100, limit * 2)}  # Reddit max is 100

        response = self.client.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        posts = []

        for child in data.get("data", {}).get("children", []):
            post_data = child.get("data", {})

            # Filter: only self posts (text posts) with content
            if not post_data.get("is_self", False):
                continue

            selftext = post_data.get("selftext", "").strip()
            if not selftext or len(selftext) < min_content_length:
                continue

            # Filter: Check timestamp if provided
            if min_timestamp:
                created_utc = post_data.get("created_utc", 0)
                if created_utc < min_timestamp:
                    continue

            post = RedditPost(
                id=post_data.get("id", ""),
                title=post_data.get("title", ""),
                content=selftext,
                subreddit=post_data.get("subreddit", subreddit_name),
                score=post_data.get("score", 0),
                url=f"https://www.reddit.com{post_data.get('permalink', '')}",
            )
            posts.append(post)

        logger.info(f"Retrieved {len(posts)} qualifying stories from r/{subreddit_name}")
        return posts

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def get_post_by_id(self, post_id: str) -> RedditPost:
        """
        Get a specific Reddit post by ID using public API.

        Args:
            post_id: Reddit post ID (e.g., 'abc123')

        Returns:
            RedditPost object
        """
        logger.info(f"Fetching post with ID: {post_id}")

        # Reddit API endpoint for single post
        url = f"https://www.reddit.com/comments/{post_id}.json"

        response = self.client.get(url)
        response.raise_for_status()

        data = response.json()

        # The response is a list where [0] contains the post data
        if not data or not isinstance(data, list) or len(data) == 0:
            raise ValueError(f"Post not found: {post_id}")

        post_data = data[0].get("data", {}).get("children", [])[0].get("data", {})

        return RedditPost(
            id=post_data.get("id", post_id),
            title=post_data.get("title", ""),
            content=post_data.get("selftext", ""),
            subreddit=post_data.get("subreddit", ""),
            score=post_data.get("score", 0),
            url=f"https://www.reddit.com{post_data.get('permalink', '')}",
        )

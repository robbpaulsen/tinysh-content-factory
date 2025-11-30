"""
Smart Cache System for TinyShorts Content Factory.

Provides intelligent caching for media assets (images, TTS) with:
- Hash-based exact matching
- Similarity-based fuzzy matching
- SQLite storage backend
- Automatic cleanup and management
"""

from .asset_cache import AssetCache

__all__ = ["AssetCache"]

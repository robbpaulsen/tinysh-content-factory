"""
Asset cache implementation with hash-based and similarity-based lookup.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import shutil

from .storage import CacheStorage
from .similarity import SimilarityMatcher


class AssetCache:
    """
    Smart cache for media assets with deduplication.

    Supports:
    - Exact hash-based lookup (fast)
    - Similarity-based fuzzy matching (slower, but finds near-duplicates)
    - Automatic file management
    - Usage statistics
    """

    def __init__(
        self,
        cache_dir: Path,
        db_path: Optional[Path] = None,
        similarity_threshold: float = 0.85,
        enable_similarity: bool = True,
    ):
        """
        Initialize asset cache.

        Args:
            cache_dir: Directory for cached files
            db_path: Path to SQLite database (defaults to cache_dir/cache.db)
            similarity_threshold: Threshold for similarity matching (0-1)
            enable_similarity: Whether to enable similarity matching
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if db_path is None:
            db_path = self.cache_dir / "cache.db"

        self.storage = CacheStorage(db_path)
        self.similarity = SimilarityMatcher(threshold=similarity_threshold)
        self.enable_similarity = enable_similarity

        # Stats
        self.stats = {"hits": 0, "misses": 0, "similarity_hits": 0}

    def get(
        self, asset_type: str, prompt: str
    ) -> Optional[tuple[str, Dict[str, Any]]]:
        """
        Get cached asset if available.

        First tries exact hash match, then similarity match if enabled.

        Args:
            asset_type: Type of asset (image, tts)
            prompt: Prompt text

        Returns:
            (file_path, metadata) tuple or None if not found
        """
        # Try exact hash match first
        prompt_hash = self.similarity.compute_hash(prompt)
        entry = self.storage.get_by_hash(asset_type, prompt_hash)

        if entry:
            file_path = entry["file_path"]
            if Path(file_path).exists():
                self.stats["hits"] += 1
                metadata = {
                    "cache_hit": True,
                    "match_type": "exact",
                    "use_count": entry["use_count"],
                }
                return (file_path, metadata)
            else:
                # File missing, clean up entry
                self.storage.delete(entry["id"])

        # Try similarity match if enabled
        if self.enable_similarity:
            candidates = self.storage.get_all_by_type(asset_type)
            candidate_tuples = [
                (str(c["id"]), c["prompt_text"], c["file_path"])
                for c in candidates
            ]

            match = self.similarity.find_similar(prompt, candidate_tuples)
            if match:
                entry_id, similarity_score, file_path = match
                if Path(file_path).exists():
                    self.stats["similarity_hits"] += 1
                    metadata = {
                        "cache_hit": True,
                        "match_type": "similarity",
                        "similarity_score": similarity_score,
                    }
                    return (file_path, metadata)

        # No match found
        self.stats["misses"] += 1
        return None

    def put(
        self,
        asset_type: str,
        prompt: str,
        source_file: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add asset to cache.

        Args:
            asset_type: Type of asset (image, tts)
            prompt: Prompt text
            source_file: Path to file to cache
            metadata: Optional metadata to store

        Returns:
            Path to cached file
        """
        prompt_hash = self.similarity.compute_hash(prompt)

        # Create type-specific subdirectory
        type_dir = self.cache_dir / asset_type
        type_dir.mkdir(exist_ok=True)

        # Generate cache filename
        source_path = Path(source_file)
        cache_filename = f"{prompt_hash}{source_path.suffix}"
        cache_path = type_dir / cache_filename

        # Copy file to cache
        shutil.copy2(source_file, cache_path)

        # Store in database
        self.storage.insert(
            asset_type=asset_type,
            prompt_hash=prompt_hash,
            prompt_text=prompt,
            file_path=str(cache_path),
            metadata=metadata,
        )

        return str(cache_path)

    def clear(self, asset_type: Optional[str] = None) -> int:
        """
        Clear cache entries and files.

        Args:
            asset_type: Optional type to clear (clears all if None)

        Returns:
            Number of entries cleared
        """
        if asset_type:
            entries = self.storage.get_all_by_type(asset_type)
        else:
            # Get all entries
            entries = []
            for atype in ["image", "tts"]:
                entries.extend(self.storage.get_all_by_type(atype))

        count = 0
        for entry in entries:
            # Delete file if exists
            file_path = Path(entry["file_path"])
            if file_path.exists():
                file_path.unlink()

            # Delete DB entry
            self.storage.delete(entry["id"])
            count += 1

        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        db_stats = self.storage.get_stats()

        return {
            "session": self.stats,
            "database": db_stats,
            "hit_rate": (
                self.stats["hits"]
                / (self.stats["hits"] + self.stats["misses"])
                if (self.stats["hits"] + self.stats["misses"]) > 0
                else 0.0
            ),
        }

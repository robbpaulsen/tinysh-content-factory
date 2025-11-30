"""
Similarity matching for fuzzy cache lookups.

Uses simple embedding-based comparison to find similar prompts
that might be good enough to reuse instead of generating new assets.
"""

from typing import List, Tuple, Optional
import hashlib


class SimilarityMatcher:
    """Simple similarity matcher for cache lookups."""

    def __init__(self, threshold: float = 0.85):
        """
        Initialize similarity matcher.

        Args:
            threshold: Similarity threshold (0-1) for considering a match
        """
        self.threshold = threshold

    def compute_hash(self, text: str) -> str:
        """
        Compute hash for a text prompt.

        Args:
            text: Text to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(text.encode()).hexdigest()

    def find_similar(
        self,
        query_text: str,
        candidates: List[Tuple[str, str, str]],  # (id, prompt_text, file_path)
    ) -> Optional[Tuple[str, float, str]]:
        """
        Find most similar candidate to query.

        Args:
            query_text: Query prompt text
            candidates: List of (id, prompt_text, file_path) tuples

        Returns:
            (id, similarity_score, file_path) or None if no match above threshold
        """
        if not candidates:
            return None

        # For now, use simple token-based similarity
        # TODO: Could be enhanced with sentence-transformers embeddings
        query_tokens = set(self._tokenize(query_text))

        best_match = None
        best_score = 0.0

        for entry_id, prompt_text, file_path in candidates:
            candidate_tokens = set(self._tokenize(prompt_text))
            score = self._jaccard_similarity(query_tokens, candidate_tokens)

            if score > best_score:
                best_score = score
                best_match = (entry_id, score, file_path)

        if best_match and best_score >= self.threshold:
            return best_match

        return None

    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization.

        Args:
            text: Text to tokenize

        Returns:
            List of lowercase tokens
        """
        # Simple whitespace tokenization with lowercasing
        return text.lower().split()

    def _jaccard_similarity(self, set1: set, set2: set) -> float:
        """
        Compute Jaccard similarity between two sets.

        Args:
            set1: First set
            set2: Second set

        Returns:
            Similarity score (0-1)
        """
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

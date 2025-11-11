"""Common retry decorators for API calls.

This module provides reusable retry logic to avoid duplication across services.
All retry decorators use exponential backoff with configurable parameters.
"""

from tenacity import retry, stop_after_attempt, wait_exponential

# Default retry configuration used across most API calls
# - 3 attempts maximum
# - Exponential backoff: 2s, 4s, 8s (multiplier=1, min=2, max=10)
# - Re-raises the exception after all attempts fail
default_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)

# Aggressive retry for critical operations (more attempts)
aggressive_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    reraise=True,
)

# Conservative retry for rate-limited APIs (fewer attempts, longer waits)
# ⚠️ Use with caution - some APIs block on excessive retries
conservative_retry = retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=2, min=5, max=30),
    reraise=True,
)

__all__ = ["default_retry", "aggressive_retry", "conservative_retry"]

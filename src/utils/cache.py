"""Caching utilities for performance optimization.

Provides caching mechanisms for expensive operations like:
- Profile configuration loading
- Settings validation
- File I/O operations

Note: These are simple in-memory caches. For distributed systems,
consider Redis or similar solutions.
"""

import asyncio
from functools import wraps
from typing import Any, Callable


class cached_property:
    """Descriptor for cached class properties.

    Similar to @property but caches the result after first access.
    Useful for expensive computations that don't change during object lifetime.

    Example:
        >>> class MyClass:
        ...     @cached_property
        ...     def expensive_operation(self):
        ...         # Only computed once
        ...         return compute_something()
    """

    def __init__(self, func: Callable):
        self.func = func
        self.attrname = None
        self.__doc__ = func.__doc__

    def __set_name__(self, owner, name):
        self.attrname = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        # Check if value is already cached
        cache = instance.__dict__
        if self.attrname in cache:
            return cache[self.attrname]

        # Compute and cache the value
        value = self.func(instance)
        cache[self.attrname] = value
        return value


def lru_cache_async(maxsize: int = 128):
    """LRU cache decorator for async functions.

    Similar to functools.lru_cache but works with async functions.
    Caches based on function arguments.

    Args:
        maxsize: Maximum number of cached results

    Example:
        >>> @lru_cache_async(maxsize=100)
        ... async def fetch_data(key: str):
        ...     return await expensive_api_call(key)
    """
    def decorator(func: Callable):
        cache = {}
        cache_order = []

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from arguments
            key = (args, tuple(sorted(kwargs.items())))

            # Return cached value if exists
            if key in cache:
                return cache[key]

            # Compute value
            result = await func(*args, **kwargs)

            # Add to cache with LRU eviction
            cache[key] = result
            cache_order.append(key)

            # Evict oldest if cache is full
            if len(cache_order) > maxsize:
                oldest_key = cache_order.pop(0)
                cache.pop(oldest_key, None)

            return result

        # Add cache_info method for debugging
        def cache_info():
            return {
                "hits": 0,  # Not tracked for simplicity
                "misses": 0,
                "size": len(cache),
                "maxsize": maxsize,
            }

        wrapper.cache_info = cache_info
        wrapper.cache_clear = lambda: (cache.clear(), cache_order.clear())

        return wrapper

    return decorator


__all__ = ["cached_property", "lru_cache_async"]

#!/usr/bin/env python3
"""
Shared cache management utilities for OLX Phone Analyzer
Provides disk-based JSON caching for API responses
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from src.infrastructure.atomic import write_json_atomic


class CustomCache:  # TODO: consider using at least cachetools/diskcache/etc
    """
    Disk-based JSON cache manager for API responses

    Note: For production use, consider alternatives like:
    - diskcache: Persistent disk-based cache with advanced features
    - cachetools: In-memory caching with TTL support
    - Redis: For distributed caching

    Current implementation is lightweight, dependency-free, and sufficient for this use case.
    """

    def __init__(self, cache_file: Path, logger):
        """
        Initialize cache manager

        Args:
            cache_file: Path to cache file
            logger: Logger instance for logging cache operations
        """
        self.cache_file = cache_file
        self.logger = logger
        self.cache: dict[str, Any] = self.load()

    def load(self) -> dict[str, Any]:
        """Load cache from disk"""
        if self.cache_file.exists():
            try:
                with Path.open(self.cache_file, encoding="utf-8") as f:
                    cache: dict[Any, Any] = json.load(f)
                    self.logger.info(
                        f"📦 Loaded {len(cache)} cached responses from {self.cache_file.name}"
                    )
                    return cache
            except Exception as e:
                self.logger.warning(f"Failed to load cache from {self.cache_file}: {e}")
                return {}
        return {}

    def save(self):
        """Save cache to disk"""
        try:
            # Ensure parent directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            write_json_atomic(self.cache_file, self.cache)
            self.logger.debug(
                f"💾 Cache saved ({len(self.cache)} entries) to {self.cache_file.name}"
            )
        except Exception as e:
            self.logger.error(f"Failed to save cache to {self.cache_file}: {e}")

    def get(self, key: str) -> Any | None:
        """Get cached value by key"""
        return self.cache.get(key)

    def set(self, key: str, value: Any):
        """Set cached value and save to disk"""
        self.cache[key] = value
        self.save()

    def has(self, key: str) -> bool:
        """Check if key exists in cache"""
        return key in self.cache

    def clear(self):
        """Clear all cached data"""
        self.cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        self.logger.info(f"🗑️  Cache cleared: {self.cache_file.name}")

    @staticmethod
    def generate_phone_cache_key(phone_data: dict[str, Any]) -> str:
        """
        Generate unique cache key for a phone listing

        Args:
            phone_data: Phone listing data

        Returns:
            MD5 hash of URL or title+price
        """
        url = phone_data.get("url", "")
        if url:
            return hashlib.md5(url.encode()).hexdigest()

        title = phone_data.get("title", "")
        price = phone_data.get("price", 0)
        key_str = f"{title}_{price}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def __len__(self) -> int:
        """Return number of cached items"""
        return len(self.cache)

    def __contains__(self, key: str) -> bool:
        """Check if key exists in cache using 'in' operator"""
        return key in self.cache

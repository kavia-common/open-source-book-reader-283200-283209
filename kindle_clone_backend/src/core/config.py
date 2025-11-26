"""
Core configuration utilities for the backend service.

This module centralizes environment configuration using python-dotenv (if available)
so that other parts of the application can import configuration in a consistent way,
without directly reading environment variables in multiple places.

Environment variables:
- CONTENT_ROOT: Root directory on filesystem where cached content and indexes are stored.
                Defaults to "./data/content" if not provided.
- CACHE_TTL:    Time-to-live for cached metadata entries, in seconds. If the current
                time exceeds (created_at + CACHE_TTL), the metadata is considered stale.
                Defaults to "86400" (24 hours) if not provided.

Note:
- Do not hardcode configuration; ensure the orchestrator sets values in the .env file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

# Attempt to load a local .env if present. This is safe in all environments.
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()  # load variables from a .env file if available
except Exception:
    # If python-dotenv is not available or any unexpected error occurs,
    # we silently ignore it and rely on the environment.
    pass


@dataclass(frozen=True)
class AppConfig:
    """Immutable app configuration values resolved from environment."""

    content_root: str
    cache_ttl_seconds: int

    @staticmethod
    # PUBLIC_INTERFACE
    def from_env(
        default_content_root: str = "./data/content",
        default_cache_ttl: int = 60 * 60 * 24,  # 24 hours
    ) -> "AppConfig":
        """
        Create an AppConfig instance by reading environment variables.

        Returns:
            AppConfig: Resolved configuration object with validated values.
        """
        content_root = os.getenv("CONTENT_ROOT", default_content_root)
        ttl_raw: Optional[str] = os.getenv("CACHE_TTL", str(default_cache_ttl))
        try:
            cache_ttl_seconds = int(ttl_raw) if ttl_raw is not None else default_cache_ttl
        except ValueError:
            cache_ttl_seconds = default_cache_ttl

        # Normalize content_root to absolute path for consistency
        content_root = os.path.abspath(content_root)
        return AppConfig(content_root=content_root, cache_ttl_seconds=cache_ttl_seconds)


# Singleton-style accessors

# PUBLIC_INTERFACE
def get_config() -> AppConfig:
    """Get the current resolved AppConfig (reads env on each call)."""
    return AppConfig.from_env()

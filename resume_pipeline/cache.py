"""
Caching utilities for resume pipeline.
"""

from pathlib import Path
from typing import Optional
from .models import CachedPipelineState


class CacheManager:
    """Manages pipeline state caching."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def save(self, cache_key: str, state: CachedPipelineState):
        """Save pipeline state to cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        cache_file.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        print(f"  ✓ Saved to cache: {cache_key[:8]}...")

    def load(self, cache_key: str) -> Optional[CachedPipelineState]:
        """Load pipeline state from cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                cached = CachedPipelineState.model_validate_json(
                    cache_file.read_text(encoding="utf-8")
                )
                print(f"  ✓ Loaded from cache: {cache_key[:8]}...")
                return cached
            except Exception as e:
                print(f"  ⚠ Cache read failed: {e}")
                return None
        return None

    def clear(self):
        """Clear all cached states."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        print(f"  ✓ Cache cleared")

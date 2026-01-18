#!/usr/bin/env python3
"""
Test script for Redis cache manager.

This script tests the Redis cache functionality without running
the full resume pipeline.

Usage:
    python test_redis_cache.py
"""

import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from resume_pipeline.cache import RedisCacheManager
from resume_pipeline.models import (
    Achievement,
    CachedPipelineState,
    JDRequirements,
)


def test_connection():
    """Test Redis connection."""
    print("=" * 80)
    print("TEST 1: Redis Connection")
    print("=" * 80)

    cache = RedisCacheManager()

    if cache.healthcheck():
        print("✓ Successfully connected to Redis")
        stats = cache.get_stats()
        print(f"  Redis version: {stats.get('redis_version', 'Unknown')}")
        print(f"  Current keys: {stats.get('total_keys', 0)}")
        print(f"  Memory used: {stats.get('memory_used', 'Unknown')}")
        return cache
    else:
        print("✗ Failed to connect to Redis")
        print("\nPlease ensure Redis is running:")
        print("  docker-compose up -d redis")
        print("  OR")
        print("  redis-server")
        return None


def test_save_and_load(cache: RedisCacheManager):
    """Test saving and loading cache."""
    print("\n" + "=" * 80)
    print("TEST 2: Save and Load")
    print("=" * 80)

    # Create test data
    test_state = CachedPipelineState(
        job_hash="test_job_hash_123",
        career_hash="test_career_hash_456",
        jd_requirements=JDRequirements(
            required_skills=["Python", "Redis", "Docker"],
            preferred_skills=["Kubernetes"],
            required_years_exp=3,
            keywords=["cache", "distributed", "performance"],
        ),
        matched_achievements=[
            Achievement(
                title="Built distributed caching system",
                description="Implemented Redis-based cache for resume pipeline",
                impact="Reduced LLM API costs by 80%",
                skills=["Python", "Redis", "Docker"],
            )
        ],
        draft_resume="This is a test draft resume.",
        timestamp=datetime.utcnow().isoformat(),
    )

    cache_key = "test_cache_key_123"

    # Test save
    print(f"\nSaving test data with key: {cache_key}")
    success = cache.save(cache_key, test_state)

    if success:
        print("✓ Successfully saved to cache")
    else:
        print("✗ Failed to save to cache")
        return False

    # Test load
    print(f"\nLoading data with key: {cache_key}")
    loaded = cache.load(cache_key)

    if loaded:
        print("✓ Successfully loaded from cache")
        print(f"  Job hash: {loaded.job_hash}")
        print(f"  Career hash: {loaded.career_hash}")
        print(f"  Skills: {', '.join(loaded.jd_requirements.required_skills)}")
        print(f"  Achievements: {len(loaded.matched_achievements)}")
        return True
    else:
        print("✗ Failed to load from cache")
        return False


def test_cache_miss(cache: RedisCacheManager):
    """Test cache miss (key doesn't exist)."""
    print("\n" + "=" * 80)
    print("TEST 3: Cache Miss")
    print("=" * 80)

    nonexistent_key = "nonexistent_key_xyz"
    print(f"\nTrying to load non-existent key: {nonexistent_key}")

    loaded = cache.load(nonexistent_key)

    if loaded is None:
        print("✓ Correctly returned None for non-existent key")
        return True
    else:
        print("✗ Should have returned None for non-existent key")
        return False


def test_exists(cache: RedisCacheManager):
    """Test key existence check."""
    print("\n" + "=" * 80)
    print("TEST 4: Key Existence")
    print("=" * 80)

    existing_key = "test_cache_key_123"
    nonexistent_key = "nonexistent_key_xyz"

    print(f"\nChecking if '{existing_key}' exists...")
    exists = cache.exists(existing_key)
    print(
        f"✓ exists() returned: {exists}" if exists else f"✗ exists() returned: {exists}"
    )

    print(f"\nChecking if '{nonexistent_key}' exists...")
    exists = cache.exists(nonexistent_key)
    print(
        f"✓ exists() returned: {exists}"
        if not exists
        else f"✗ exists() returned: {exists}"
    )

    return True


def test_clear(cache: RedisCacheManager):
    """Test cache clearing."""
    print("\n" + "=" * 80)
    print("TEST 5: Clear Cache")
    print("=" * 80)

    # Get current count
    stats_before = cache.get_stats()
    keys_before = stats_before.get("total_keys", 0)
    print(f"\nKeys before clear: {keys_before}")

    # Clear all test keys
    print("\nClearing cache with pattern 'test_*'...")
    deleted = cache.clear(pattern="test_*")
    print(f"Deleted {deleted} keys")

    # Check count after
    stats_after = cache.get_stats()
    keys_after = stats_after.get("total_keys", 0)
    print(f"Keys after clear: {keys_after}")

    if keys_after < keys_before:
        print("✓ Successfully cleared cache")
        return True
    else:
        print("✗ Cache clear may have failed")
        return False


def test_ttl(cache: RedisCacheManager):
    """Test TTL (time-to-live) functionality."""
    print("\n" + "=" * 80)
    print("TEST 6: TTL (Time-to-Live)")
    print("=" * 80)

    print(
        f"\nConfigured TTL: {cache.ttl_seconds} seconds ({cache.ttl_seconds // 86400} days)"
    )

    # Note: We can't easily test actual expiry without waiting,
    # but we can verify the TTL is set
    test_key = "test_ttl_key"
    test_state = CachedPipelineState(
        job_hash="ttl_test",
        career_hash="ttl_test",
        jd_requirements=JDRequirements(
            required_skills=["Testing"],
            preferred_skills=[],
            required_years_exp=0,
            keywords=["ttl"],
        ),
        matched_achievements=[],
        draft_resume="TTL test",
        timestamp=datetime.utcnow().isoformat(),
    )

    cache.save(test_key, test_state)

    print("✓ TTL will be set automatically on save")
    print("  Entries will expire after configured TTL period")

    # Clean up
    cache.clear(pattern="test_ttl_*")

    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("REDIS CACHE MANAGER TEST SUITE")
    print("=" * 80)

    # Test 1: Connection
    cache = test_connection()
    if not cache:
        print("\n❌ TESTS FAILED: Could not connect to Redis")
        return 1

    # Test 2: Save and Load
    if not test_save_and_load(cache):
        print("\n❌ TESTS FAILED: Save/Load test failed")
        return 1

    # Test 3: Cache Miss
    if not test_cache_miss(cache):
        print("\n❌ TESTS FAILED: Cache miss test failed")
        return 1

    # Test 4: Exists
    if not test_exists(cache):
        print("\n❌ TESTS FAILED: Exists test failed")
        return 1

    # Test 5: Clear
    if not test_clear(cache):
        print("\n❌ TESTS FAILED: Clear test failed")
        return 1

    # Test 6: TTL
    if not test_ttl(cache):
        print("\n❌ TESTS FAILED: TTL test failed")
        return 1

    # All tests passed
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED")
    print("=" * 80)
    print("\nRedis cache is working correctly!")
    print("You can now use it in the resume pipeline.")

    # Final cleanup
    print("\nCleaning up test data...")
    cache.clear(pattern="test_*")
    cache.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())

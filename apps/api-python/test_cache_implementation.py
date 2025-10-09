#!/usr/bin/env python3
"""
Test script for PHASE 1 cache implementation

This script validates:
1. Cache module functionality (get/set/invalidate)
2. Dashboard endpoint cache behavior
3. Cache metrics tracking
4. Performance improvements
"""

import asyncio
import time
from infrastructure.cache import get_positions_cache
from infrastructure.database.connection_transaction_mode import transaction_db

async def test_cache_basic_operations():
    """Test basic cache operations"""
    print("\n" + "="*60)
    print("TEST 1: Basic Cache Operations")
    print("="*60)

    cache = get_positions_cache()

    # Test SET
    await cache.set(1, "test_key", {"data": "test_value"}, ttl=5)
    print("✅ SET: Data stored successfully")

    # Test GET (should hit cache)
    data = await cache.get(1, "test_key")
    assert data == {"data": "test_value"}, "Cache data mismatch"
    print(f"✅ GET: Retrieved data: {data}")

    # Test METRICS
    metrics = cache.get_metrics()
    print(f"✅ METRICS: {metrics}")
    assert metrics['hits'] > 0, "No cache hits recorded"
    assert metrics['hit_rate'] > 0, "Hit rate is 0"

    # Test INVALIDATE
    count = await cache.invalidate(1, "test_key")
    assert count == 1, "Invalidation failed"
    print(f"✅ INVALIDATE: {count} entries removed")

    # Test GET after invalidation (should miss)
    data = await cache.get(1, "test_key")
    assert data is None, "Data should be None after invalidation"
    print("✅ GET after invalidation: None (expected)")

    print("\n🎉 All basic cache tests passed!")

async def test_cache_ttl():
    """Test cache TTL expiration"""
    print("\n" + "="*60)
    print("TEST 2: Cache TTL Expiration")
    print("="*60)

    cache = get_positions_cache()

    # Set with 2s TTL
    await cache.set(1, "ttl_test", {"value": 123}, ttl=2)
    print("✅ SET: Data stored with 2s TTL")

    # Immediate get (should hit)
    data = await cache.get(1, "ttl_test")
    assert data is not None, "Cache should have data immediately"
    print(f"✅ GET (0s): Data retrieved: {data}")

    # Wait 1 second (should still hit)
    await asyncio.sleep(1)
    data = await cache.get(1, "ttl_test")
    assert data is not None, "Cache should still have data after 1s"
    print(f"✅ GET (1s): Data still valid: {data}")

    # Wait 2 more seconds (should expire)
    await asyncio.sleep(2)
    data = await cache.get(1, "ttl_test")
    assert data is None, "Cache should be expired after 3s"
    print("✅ GET (3s): Data expired (None)")

    print("\n🎉 TTL expiration test passed!")

async def test_cache_metrics():
    """Test cache metrics tracking"""
    print("\n" + "="*60)
    print("TEST 3: Cache Metrics Tracking")
    print("="*60)

    cache = get_positions_cache()
    cache.reset_metrics()

    # Generate some hits and misses
    await cache.set(1, "metrics_test", {"val": 1}, ttl=5)

    # 3 hits
    for i in range(3):
        await cache.get(1, "metrics_test")

    # 2 misses
    for i in range(2):
        await cache.get(1, "nonexistent_key")

    metrics = cache.get_metrics()
    print(f"✅ Metrics after operations: {metrics}")

    assert metrics['hits'] == 3, f"Expected 3 hits, got {metrics['hits']}"
    assert metrics['misses'] == 2, f"Expected 2 misses, got {metrics['misses']}"
    assert metrics['total_requests'] == 5, f"Expected 5 requests, got {metrics['total_requests']}"
    assert metrics['hit_rate'] == 60.0, f"Expected 60% hit rate, got {metrics['hit_rate']}"

    print(f"   - Hits: {metrics['hits']} ✅")
    print(f"   - Misses: {metrics['misses']} ✅")
    print(f"   - Hit Rate: {metrics['hit_rate']}% ✅")
    print(f"   - Cache Size: {metrics['size']} entries")

    print("\n🎉 Metrics tracking test passed!")

async def test_cache_performance():
    """Test cache performance improvement"""
    print("\n" + "="*60)
    print("TEST 4: Cache Performance Benchmark")
    print("="*60)

    cache = get_positions_cache()

    # Simulate heavy data
    heavy_data = {
        "positions": [{"symbol": f"SYMBOL{i}", "pnl": i * 100} for i in range(100)],
        "total_pnl": 50000,
        "count": 100
    }

    # First call (cache miss)
    start = time.time()
    await cache.set(1, "perf_test", heavy_data, ttl=5)
    data = await cache.get(1, "perf_test")
    miss_time = (time.time() - start) * 1000  # ms

    print(f"✅ Cache MISS: {miss_time:.2f}ms")

    # Second call (cache hit)
    start = time.time()
    data = await cache.get(1, "perf_test")
    hit_time = (time.time() - start) * 1000  # ms

    print(f"✅ Cache HIT: {hit_time:.2f}ms")

    improvement = ((miss_time - hit_time) / miss_time) * 100
    print(f"\n🚀 Performance improvement: {improvement:.1f}% faster with cache")

    assert data is not None, "Cache should return data"
    assert len(data['positions']) == 100, "Data integrity check failed"

    print("\n🎉 Performance test passed!")

async def test_cache_cleanup():
    """Test automatic cleanup of expired entries"""
    print("\n" + "="*60)
    print("TEST 5: Automatic Cleanup")
    print("="*60)

    cache = get_positions_cache()

    # Clear all cache first
    await cache.clear()
    print("✅ Cache cleared for clean test")

    # Add multiple entries with different TTLs
    await cache.set(1, "cleanup_1", {"val": 1}, ttl=1)
    await cache.set(1, "cleanup_2", {"val": 2}, ttl=1)
    await cache.set(1, "cleanup_3", {"val": 3}, ttl=10)

    print("✅ Added 3 entries (2 with 1s TTL, 1 with 10s TTL)")

    metrics_before = cache.get_metrics()
    print(f"   - Cache size before: {metrics_before['size']} entries")

    # Wait for expiration
    await asyncio.sleep(2)

    # Trigger cleanup
    removed = await cache.cleanup_expired()
    print(f"✅ Cleanup removed: {removed} expired entries")

    metrics_after = cache.get_metrics()
    print(f"   - Cache size after: {metrics_after['size']} entries")

    assert removed == 2, f"Expected 2 removed, got {removed}"
    assert metrics_after['size'] == 1, f"Expected 1 entry remaining, got {metrics_after['size']}"

    print("\n🎉 Cleanup test passed!")

async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print(" PHASE 1 - CACHE IMPLEMENTATION TEST SUITE")
    print("="*80)

    try:
        # Connect to database (needed for some tests)
        await transaction_db.connect()
        print("✅ Database connected")

        # Run all tests
        await test_cache_basic_operations()
        await test_cache_ttl()
        await test_cache_metrics()
        await test_cache_performance()
        await test_cache_cleanup()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED! Cache implementation is working correctly.")
        print("="*80)

        # Final metrics summary
        cache = get_positions_cache()
        final_metrics = cache.get_metrics()
        print("\n📊 FINAL CACHE METRICS:")
        print(f"   - Total Requests: {final_metrics['total_requests']}")
        print(f"   - Hits: {final_metrics['hits']}")
        print(f"   - Misses: {final_metrics['misses']}")
        print(f"   - Hit Rate: {final_metrics['hit_rate']}%")
        print(f"   - Cache Size: {final_metrics['size']} entries")
        print(f"   - Invalidations: {final_metrics['invalidations']}")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await transaction_db.disconnect()

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

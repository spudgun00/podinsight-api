#!/usr/bin/env python3
"""
Direct test of warm performance to diagnose the 3.3s issue
"""

import modal
import time

# Connect to the deployed app
app = modal.App.lookup("snapshot-test")
SnapshotTest = modal.Cls.lookup("snapshot-test", "SnapshotTest")

def test_performance():
    """Test actual performance with detailed timing"""
    print("🔍 Testing warm performance...")

    # Get instance
    model = SnapshotTest()

    # First call (might be cold)
    print("\n1️⃣ First call:")
    start = time.time()
    result1 = model.test.remote()
    elapsed1 = time.time() - start
    print(f"   Total time: {elapsed1:.3f}s")
    print(f"   Encode time: {result1.get('encode_time_ms', 0):.1f}ms")
    print(f"   GPU available: {result1.get('gpu_available', False)}")
    print(f"   Cold start: {result1.get('cold_start', 'unknown')}")

    # Second call (definitely warm)
    print("\n2️⃣ Second call (warm):")
    start = time.time()
    result2 = model.test.remote()
    elapsed2 = time.time() - start
    print(f"   Total time: {elapsed2:.3f}s")
    print(f"   Encode time: {result2.get('encode_time_ms', 0):.1f}ms")

    # Third call
    print("\n3️⃣ Third call (warm):")
    start = time.time()
    result3 = model.test.remote()
    elapsed3 = time.time() - start
    print(f"   Total time: {elapsed3:.3f}s")
    print(f"   Encode time: {result3.get('encode_time_ms', 0):.1f}ms")

    # Analysis
    print("\n📊 Analysis:")
    avg_warm = (elapsed2 + elapsed3) / 2
    print(f"   Average warm time: {avg_warm:.3f}s")

    if avg_warm < 0.5:
        print("   ✅ Excellent warm performance!")
    elif avg_warm < 1.0:
        print("   ⚠️ Warm performance is slower than expected")
        print("   Expected: ~400ms, Actual: {:.0f}ms".format(avg_warm * 1000))
    else:
        print("   ❌ Warm performance is too slow!")
        print("   This suggests GPU may not be used or test overhead")

    # Check snapshot status
    try:
        is_snapshot = model.is_snapshot.remote()
        print(f"\n📸 Container from snapshot: {is_snapshot}")
    except:
        print("\n📸 Could not check snapshot status")

if __name__ == "__main__":
    print("🚀 Modal Warm Performance Test")
    print("=" * 50)
    test_performance()

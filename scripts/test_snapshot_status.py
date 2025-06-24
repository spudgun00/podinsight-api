#!/usr/bin/env python3
"""
Test script to check if Modal snapshots are working
Uses the advisor's recommended is_snapshot method
"""

import modal
import time
import sys

# Connect to the deployed app
app = modal.App.lookup("snapshot-test")

# Get the SnapshotTest class
SnapshotTest = modal.Cls.lookup("snapshot-test", "SnapshotTest")

def test_snapshot_status():
    """Test if the container was restored from a snapshot"""
    print("🔍 Checking snapshot status...")
    
    # Create an instance
    model = SnapshotTest()
    
    # Check if restored from snapshot
    try:
        is_snapshot = model.is_snapshot.remote()
        print(f"\n📸 Snapshot status: {is_snapshot}")
        
        if is_snapshot is True:
            print("✅ Container was restored from snapshot!")
            print("   This means snapshots are working correctly.")
        elif is_snapshot is False:
            print("❌ Container was NOT restored from snapshot")
            print("   This is expected for the first container after deploy.")
            print("   Wait 12+ minutes and try again.")
        else:
            print("⚠️  Could not determine snapshot status")
            print("   The modal.current_snapshot_is_restored() function may not be available")
    except Exception as e:
        print(f"❌ Error checking snapshot status: {e}")
        return False
    
    # Run a test to measure performance
    print("\n⏱️  Testing performance...")
    start = time.time()
    result = model.test.remote()
    elapsed = time.time() - start
    
    print(f"\n📊 Performance results:")
    print(f"   Total time: {elapsed:.2f}s")
    print(f"   Cold start: {result.get('cold_start', 'unknown')}")
    print(f"   Inference time: {result.get('time_ms', 0):.1f}ms")
    print(f"   Embedding dimension: {result.get('embedding_dim', 0)}")
    
    # Interpret results
    print("\n🎯 Analysis:")
    if elapsed < 7:
        print("   ✅ Excellent! Cold start under 7s indicates snapshots are working")
    elif elapsed < 15:
        print("   ⚠️  Moderate performance - snapshots may be partially working")
    else:
        print("   ❌ Slow cold start - snapshots don't appear to be working yet")
    
    return is_snapshot

def wait_and_test():
    """Wait for container to scale down and test again"""
    print("\n⏳ Waiting for container to scale down...")
    print("   Container scales down after 10 minutes")
    print("   Cron runs every 12 minutes")
    print("   This ensures a true cold start test")
    
    # Check current status
    is_snapshot = test_snapshot_status()
    
    if is_snapshot is False:
        print("\n💡 Recommendation:")
        print("   1. Wait 12-15 minutes for container to fully scale down")
        print("   2. Run this script again: python scripts/test_snapshot_status.py")
        print("   3. You should see 'true' for snapshot status")
        print("   4. Cold start should be under 6 seconds")

if __name__ == "__main__":
    print("🚀 Modal Snapshot Status Test")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--wait":
        wait_and_test()
    else:
        test_snapshot_status()
        print("\n💡 Tip: Run with --wait flag to see recommendations")
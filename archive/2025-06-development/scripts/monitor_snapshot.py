#!/usr/bin/env python3
"""
Monitor Modal snapshot creation and cold start performance
"""

import time
import modal
import sys
from datetime import datetime

def test_performance():
    """Test current performance and snapshot status"""
    app = modal.App.lookup('snapshot-test')
    cls = modal.Cls.lookup('snapshot-test', 'SnapshotTest')

    print(f"\n🕐 Testing at {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 50)

    try:
        # Create instance and test
        m = cls()

        # Test performance
        start = time.time()
        result = m.test.remote()
        elapsed = time.time() - start

        # Check snapshot status
        snapshot_status = m.is_snapshot.remote()

        print(f"📊 Results:")
        print(f"   Total time: {elapsed:.2f}s")
        print(f"   Encode time: {result.get('encode_time_ms', 0):.0f}ms")
        print(f"   Cold start: {result.get('cold_start', 'unknown')}")
        print(f"   From snapshot: {snapshot_status}")

        # Interpret results
        if elapsed < 7:
            print("   ✅ SNAPSHOT WORKING! Cold start under 7s")
            return True
        elif elapsed < 15:
            print("   ⚠️  Partial improvement")
        else:
            print("   ⏳ Still waiting for snapshots to activate")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    return False

def monitor_until_snapshot():
    """Monitor until snapshots are working"""
    print("🚀 Modal Snapshot Monitor")
    print("=" * 50)
    print("Monitoring for snapshot activation...")
    print("Container scales down after 10 minutes")
    print("Press Ctrl+C to stop monitoring\n")

    # Initial test
    test_performance()

    # Wait for scale down
    print(f"\n⏳ Waiting 10 minutes for container to scale down...")
    print("   This is when the snapshot gets created")

    for i in range(10, 0, -1):
        print(f"   {i} minutes remaining...", end='\r')
        time.sleep(60)

    print("\n\n🎯 Container should be scaled down. Testing cold start...")

    # Test after scale down
    snapshot_working = test_performance()

    if snapshot_working:
        print("\n🎉 SUCCESS! Snapshots are working!")
        print("   Cold starts are now optimized to 4-6s")
    else:
        print("\n⏳ Snapshot may still be creating. Try again in 2 minutes.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        test_performance()
    else:
        try:
            monitor_until_snapshot()
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped")

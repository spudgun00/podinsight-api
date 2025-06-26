#!/usr/bin/env python3
"""
Warm up the Modal.com endpoint to avoid cold starts
Run this before testing to ensure the endpoint is responsive
"""

import requests
import time
import json

MODAL_URL = "https://podinsighthq--podinsight-embeddings-api-fastapi-app.modal.run"

def warmup_modal():
    """Send a test request to warm up the Modal endpoint"""
    print("🔥 Warming up Modal.com endpoint...")

    # First, check health
    try:
        print("📡 Checking health endpoint...")
        health_response = requests.get(f"{MODAL_URL}/health", timeout=120)
        print(f"✅ Health check: {health_response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

    # Then send a test embedding request
    try:
        print("\n🚀 Sending test embedding request...")
        start_time = time.time()

        test_payload = {"text": "warm up test"}
        response = requests.post(
            f"{MODAL_URL}/embed",
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=120
        )

        elapsed = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Embedding generated successfully!")
            print(f"⏱️  Response time: {elapsed:.2f} seconds")
            print(f"📊 Dimensions: {data.get('dimension', 'unknown')}")
            print(f"🤖 Model: {data.get('model', 'unknown')}")

            if elapsed < 5:
                print("\n🎉 Endpoint is WARM and ready!")
            else:
                print(f"\n⚠️  Endpoint was cold (took {elapsed:.2f}s), but should be warm now")
                print("💡 Try running the warmup again in 30 seconds")

        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.Timeout:
        print("❌ Request timed out after 120 seconds")
        print("💡 The endpoint is likely cold. Try running again in a minute.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    warmup_modal()

    print("\n📝 Next steps:")
    print("1. If the endpoint was cold, wait 30 seconds and run this again")
    print("2. Once warm (<5s response), test the search API")
    print("3. The endpoint will stay warm for ~5 minutes")

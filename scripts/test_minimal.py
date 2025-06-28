#!/usr/bin/env python3
"""
Minimal test to check synthesis
"""
import requests
import json

# Test with curl command instead
import subprocess

def test_with_curl():
    """Use curl to test the endpoint"""
    print("Testing with curl command...")
    
    cmd = [
        "curl", "-X", "POST",
        "https://podinsight-api.vercel.app/api/search",
        "-H", "Content-Type: application/json",
        "-d", '{"query": "AI", "limit": 1}',
        "-w", "\nStatus: %{http_code}\nTime: %{time_total}s\n",
        "--max-time", "35"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("Response:", result.stdout)
    if result.stderr:
        print("Error:", result.stderr)

if __name__ == "__main__":
    test_with_curl()
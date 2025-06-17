#!/usr/bin/env python
"""Simple test to see timing logs"""
import requests
import time

# Make a single request
print("Making request to API...")
start = time.time()
response = requests.get("http://localhost:8000/api/topic-velocity?weeks=12")
elapsed = (time.time() - start) * 1000
print(f"Total time: {elapsed:.2f}ms")
print(f"Status: {response.status_code}")

# Check the server console for timing logs
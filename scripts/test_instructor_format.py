#!/usr/bin/env python3
"""
Test Instructor-XL embedding format locally
"""

# Test the expected input format for Instructor-XL
print("Testing Instructor-XL input formats...")

# Format 1: Instruction + text pairs (recommended by Instructor)
format1 = [
    ["Represent the venture capital podcast discussion:", "AI startup valuations are increasing"],
    ["Represent the venture capital podcast discussion:", "Series A funding rounds in 2024"]
]

# Format 2: Simple text list
format2 = [
    "AI startup valuations are increasing",
    "Series A funding rounds in 2024"
]

# Format 3: Single instruction + text
format3 = [["Represent the venture capital podcast discussion:", "AI startup valuations are increasing"]]

print("\nExpected formats for Instructor-XL:")
print("Format 1 (batch with instructions):", format1)
print("Format 2 (simple text):", format2)
print("Format 3 (single with instruction):", format3)

print("\nFor Modal endpoint, we should use Format 3 for single embeddings")
print("The instruction helps the model understand the context (venture capital podcasts)")
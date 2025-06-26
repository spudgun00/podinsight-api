#!/usr/bin/env python3
"""
Test different embedding recipes using temporary Modal endpoints
This avoids needing to install the model locally
"""

import os
import asyncio
import numpy as np
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import aiohttp
from typing import List, Dict
import statistics

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MODAL_URL = "https://podinsighthq--podinsight-embeddings-simple-generate-embedding.modal.run"

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)

async def get_embedding_with_instruction(text: str, instruction: str = None) -> List[float]:
    """Get embedding from Modal endpoint with specific instruction prepended"""
    async with aiohttp.ClientSession() as session:
        # Simulate what Modal would do with different instructions
        if instruction:
            # Prepend instruction to text (this is a workaround)
            formatted_text = f"{instruction} {text}"
        else:
            formatted_text = text

        payload = {"text": formatted_text}

        async with session.post(MODAL_URL, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("embedding", [])
    return None

async def test_recipes_simple():
    """Test different embedding recipes using the current Modal endpoint"""

    print("🔍 Testing Embedding Recipes (Simple Version)")
    print("=" * 80)
    print("Note: This tests by prepending instructions to text")
    print("For exact testing, we need to modify Modal endpoint directly")
    print()

    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.podinsight

    # Get sample chunks
    print("1. Fetching sample chunks...")

    # Get chunks with different queries to ensure variety
    test_queries = ["openai", "artificial intelligence", "venture capital", "startup"]
    all_chunks = []

    for query in test_queries:
        cursor = db.transcript_chunks_768d.find(
            {"text": {"$regex": query, "$options": "i"}},
            {"_id": 0, "text": 1, "embedding_768d": 1}
        ).limit(5)

        chunks = await cursor.to_list(None)
        all_chunks.extend(chunks)

    print(f"   Found {len(all_chunks)} total chunks")

    # Test recipes
    recipes = [
        ("No instruction", None),
        ("VC podcast", "Represent the venture capital podcast discussion:"),
        ("Document", "Represent the document:"),
        ("Retrieval", "Represent this document for retrieval:"),
        ("Query prefix", "query:"),
        ("Passage prefix", "passage:"),
    ]

    print("\n2. Testing each recipe...")
    print("   (Looking for cosine similarity ≥ 0.95)")

    results = {}

    for recipe_name, instruction in recipes:
        print(f"\n   Testing: {recipe_name}")
        if instruction:
            print(f"   Instruction: '{instruction}'")

        similarities = []
        high_similarity_count = 0

        # Test first 10 chunks
        for i, chunk in enumerate(all_chunks[:10]):
            original_embedding = chunk['embedding_768d']
            text = chunk['text']

            # Get new embedding
            new_embedding = await get_embedding_with_instruction(text, instruction)

            if new_embedding:
                similarity = cosine_similarity(original_embedding, new_embedding)
                similarities.append(similarity)

                if similarity >= 0.95:
                    high_similarity_count += 1

                # Show first few
                if i < 3:
                    print(f"      Chunk {i+1}: {similarity:.4f}")

        if similarities:
            median = statistics.median(similarities)
            mean = statistics.mean(similarities)

            results[recipe_name] = {
                'median': median,
                'mean': mean,
                'high_count': high_similarity_count,
                'total': len(similarities)
            }

            print(f"   📊 Stats: Median={median:.4f}, Mean={mean:.4f}")
            print(f"   High similarity (≥0.95): {high_similarity_count}/{len(similarities)}")

    # Summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    sorted_results = sorted(results.items(), key=lambda x: x[1]['median'], reverse=True)

    best_recipe = None
    best_score = 0

    for name, stats in sorted_results:
        print(f"\n{name}:")
        print(f"  Median similarity: {stats['median']:.4f}")
        print(f"  High matches: {stats['high_count']}/{stats['total']}")

        if stats['median'] > best_score:
            best_score = stats['median']
            best_recipe = name

    print(f"\n🏆 Best recipe: {best_recipe} (median: {best_score:.4f})")

    if best_score < 0.95:
        print("\n⚠️  No recipe achieved high similarity (≥0.95)")
        print("This suggests:")
        print("1. The original embeddings used Instructor format [[instruction, text]]")
        print("2. Or used different preprocessing (lowercase, etc.)")
        print("3. Or used a different model version")
        print("\nNext step: Modify modal_web_endpoint_simple.py to test Instructor format")
    else:
        print("\n✅ Found matching recipe!")
        print("Next step: Update INSTRUCTION in modal_web_endpoint_simple.py")

    # Test a specific hypothesis
    print("\n" + "=" * 80)
    print("TESTING SPECIFIC HYPOTHESIS")
    print("=" * 80)
    print("\nLet's check if chunks were embedded with NO instruction...")

    # Get fresh chunk
    test_chunk = await db.transcript_chunks_768d.find_one(
        {"text": {"$regex": "openai", "$options": "i"}}
    )

    if test_chunk:
        text = test_chunk['text']
        original = test_chunk['embedding_768d']

        # Test with current Modal (no instruction)
        current_embedding = await get_embedding_with_instruction(text, None)

        if current_embedding:
            similarity = cosine_similarity(original, current_embedding)
            print(f"\nText preview: {text[:100]}...")
            print(f"Similarity with no instruction: {similarity:.4f}")

            if similarity >= 0.95:
                print("✅ Chunks were likely embedded with NO instruction!")
            else:
                print("❌ Chunks were NOT embedded with no instruction")

    client.close()
    print("\n✅ Analysis complete!")

if __name__ == "__main__":
    asyncio.run(test_recipes_simple())

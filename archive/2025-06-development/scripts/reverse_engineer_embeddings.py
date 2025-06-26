#!/usr/bin/env python3
"""
Reverse-engineer the original embedding recipe by comparing stored embeddings
with freshly generated ones using different instructions and preprocessing
"""

import os
import asyncio
import numpy as np
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import aiohttp
from typing import List, Tuple, Dict
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

async def get_modal_embedding(text: str) -> List[float]:
    """Get embedding from Modal endpoint (currently using no instruction)"""
    async with aiohttp.ClientSession() as session:
        payload = {"text": text}
        async with session.post(MODAL_URL, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("embedding", [])
    return None

async def get_local_embedding(text: str, instruction: str = None, preprocess: str = None) -> List[float]:
    """
    Generate embedding locally with different instructions and preprocessing
    This simulates what the Modal endpoint would do with different settings
    """
    # Import inside function to avoid issues
    try:
        from sentence_transformers import SentenceTransformer
        import torch
    except ImportError:
        print("❌ Please install: pip install sentence-transformers torch")
        return None

    # Load model (cache it globally in production)
    model = SentenceTransformer('hkunlp/instructor-xl')

    # Apply preprocessing if specified
    processed_text = text
    if preprocess == "lowercase":
        processed_text = text.lower()
    elif preprocess == "strip_punct":
        import string
        processed_text = text.translate(str.maketrans('', '', string.punctuation))
    elif preprocess == "collapse_whitespace":
        processed_text = ' '.join(text.split())

    # Format input based on instruction
    if instruction is None:
        # No instruction - just the text
        input_data = processed_text
    else:
        # Instructor format: [[instruction, text]]
        input_data = [[instruction, processed_text]]

    # Generate embedding
    embedding = model.encode(
        input_data,
        normalize_embeddings=True,
        convert_to_tensor=False,
        show_progress_bar=False
    )

    # Handle output format
    if instruction is not None and isinstance(embedding, list):
        embedding = embedding[0]

    return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)

async def test_embedding_recipes():
    """Test different embedding recipes to find the original"""

    print("🔍 Reverse-Engineering Original Embedding Recipe")
    print("=" * 80)

    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.podinsight

    # 1. Get sample chunks with known text
    print("\n1. Fetching sample chunks containing 'openai'...")
    cursor = db.transcript_chunks_768d.find(
        {"text": {"$regex": "openai", "$options": "i"}},
        {"_id": 0, "text": 1, "embedding_768d": 1}
    ).limit(30)

    chunks = await cursor.to_list(None)
    print(f"   Found {len(chunks)} chunks")

    # Also get some random chunks for broader testing
    print("\n2. Fetching random chunks for broader testing...")
    random_cursor = db.transcript_chunks_768d.aggregate([
        {"$sample": {"size": 20}},
        {"$project": {"_id": 0, "text": 1, "embedding_768d": 1}}
    ])
    random_chunks = await random_cursor.to_list(None)

    all_chunks = chunks + random_chunks
    print(f"   Total chunks to test: {len(all_chunks)}")

    # Define candidate recipes
    candidates = [
        {
            "name": "A. No instruction",
            "instruction": None,
            "preprocess": None
        },
        {
            "name": "B. VC podcast instruction",
            "instruction": "Represent the venture capital podcast discussion:",
            "preprocess": None
        },
        {
            "name": "C. Generic document instruction",
            "instruction": "Represent the document:",
            "preprocess": None
        },
        {
            "name": "D. Retrieval instruction",
            "instruction": "Represent this document for retrieval:",
            "preprocess": None
        },
        {
            "name": "E. Query instruction",
            "instruction": "query:",
            "preprocess": None
        },
        {
            "name": "F. Passage instruction",
            "instruction": "passage:",
            "preprocess": None
        },
        {
            "name": "G. No instruction + lowercase",
            "instruction": None,
            "preprocess": "lowercase"
        },
        {
            "name": "H. VC instruction + lowercase",
            "instruction": "Represent the venture capital podcast discussion:",
            "preprocess": "lowercase"
        }
    ]

    # Test each candidate
    print("\n3. Testing each embedding recipe...")
    print("   (Cosine similarity ≥ 0.95 indicates a match)")
    print()

    results = {}

    for candidate in candidates:
        print(f"\n   Testing: {candidate['name']}")
        if candidate['instruction']:
            print(f"   Instruction: '{candidate['instruction']}'")
        if candidate['preprocess']:
            print(f"   Preprocessing: {candidate['preprocess']}")

        similarities = []

        # Test on subset to avoid rate limits
        test_chunks = all_chunks[:10]  # Start with 10 chunks

        for i, chunk in enumerate(test_chunks):
            original_embedding = chunk['embedding_768d']
            text = chunk['text']

            # Generate new embedding with this recipe
            new_embedding = await get_local_embedding(
                text,
                instruction=candidate['instruction'],
                preprocess=candidate['preprocess']
            )

            if new_embedding:
                similarity = cosine_similarity(original_embedding, new_embedding)
                similarities.append(similarity)

                # Show progress
                if i < 3:  # Show first 3 scores
                    print(f"      Chunk {i+1}: {similarity:.4f}")
            else:
                print(f"      ❌ Failed to generate embedding for chunk {i+1}")

        if similarities:
            median_sim = statistics.median(similarities)
            mean_sim = statistics.mean(similarities)
            max_sim = max(similarities)
            min_sim = min(similarities)

            results[candidate['name']] = {
                'median': median_sim,
                'mean': mean_sim,
                'max': max_sim,
                'min': min_sim,
                'count': len(similarities)
            }

            print(f"   📊 Results:")
            print(f"      Median: {median_sim:.4f}")
            print(f"      Mean: {mean_sim:.4f}")
            print(f"      Range: {min_sim:.4f} - {max_sim:.4f}")

            # Flag if this looks like a match
            if median_sim >= 0.95:
                print(f"   ✅ LIKELY MATCH! High similarity detected")

    # 4. Summary
    print("\n" + "=" * 80)
    print("SUMMARY - Sorted by median similarity:")
    print("=" * 80)

    sorted_results = sorted(results.items(), key=lambda x: x[1]['median'], reverse=True)

    for name, stats in sorted_results:
        print(f"\n{name}:")
        print(f"  Median: {stats['median']:.4f}")
        print(f"  Mean: {stats['mean']:.4f}")
        print(f"  Range: {stats['min']:.4f} - {stats['max']:.4f}")

        if stats['median'] >= 0.95:
            print("  ✅ MATCH - This is likely the original recipe!")
        elif stats['median'] >= 0.8:
            print("  ⚠️  Close but not exact")

    # 5. Test current Modal endpoint
    print("\n" + "=" * 80)
    print("Testing current Modal endpoint configuration:")
    print("=" * 80)

    modal_similarities = []
    for chunk in all_chunks[:5]:
        original_embedding = chunk['embedding_768d']
        text = chunk['text']

        modal_embedding = await get_modal_embedding(text)
        if modal_embedding:
            similarity = cosine_similarity(original_embedding, modal_embedding)
            modal_similarities.append(similarity)
            print(f"  Chunk similarity: {similarity:.4f}")

    if modal_similarities:
        print(f"\nModal endpoint median similarity: {statistics.median(modal_similarities):.4f}")

    # Close connection
    client.close()

    print("\n✅ Analysis complete!")
    print("\nNext steps:")
    print("1. If a recipe scored ≥0.95, update INSTRUCTION in modal_web_endpoint_simple.py")
    print("2. Redeploy with: modal deploy scripts/modal_web_endpoint_simple.py")
    print("3. Test with queries that were failing: 'openai', 'venture capital'")

if __name__ == "__main__":
    asyncio.run(test_embedding_recipes())

import modal
from typing import List

app = modal.App("podinsight-instructor-xl")

# Create image with ML dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "sentence-transformers==2.7.0",
    "torch>=2.0.0",
    "numpy"
)

@app.function(
    image=image,
    gpu="T4",  # GPU for faster inference
    scaledown_window=300,  # Keep warm for 5 mins
    timeout=600,
)
@modal.web_endpoint(method="POST")
def embed_text(text: str) -> List[float]:
    """Generate 768D embedding for text using Instructor-XL"""
    from sentence_transformers import SentenceTransformer

    print(f"Loading Instructor-XL model...")
    model = SentenceTransformer('hkunlp/instructor-xl')
    instruction = "Represent the venture capital podcast discussion:"

    print(f"Generating embedding for: {text[:50]}...")
    embedding = model.encode([[instruction, text]])[0]

    return embedding.tolist()


@app.function(
    image=image,
    gpu="T4",
    container_idle_timeout=300,
    timeout=600,
)
def embed_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts"""
    from sentence_transformers import SentenceTransformer

    print(f"Loading model for batch of {len(texts)} texts...")
    model = SentenceTransformer('hkunlp/instructor-xl')
    instruction = "Represent the venture capital podcast discussion:"

    # Format texts with instruction
    formatted_texts = [[instruction, text] for text in texts]
    embeddings = model.encode(formatted_texts)

    return [emb.tolist() for emb in embeddings]


@app.local_entrypoint()
def main():
    """Test the embedding function"""
    # Test single embedding
    test_text = "What are the latest trends in AI venture capital?"
    print(f"\n🧪 Testing single embedding...")
    print(f"Query: {test_text}")

    result = embed_text.remote(test_text)
    print(f"✅ Generated {len(result)}-dimensional embedding")
    print(f"Sample values: {result[:5]}")

    # Test batch embedding
    print(f"\n🧪 Testing batch embedding...")
    test_batch = [
        "AI agents and automation",
        "venture capital trends",
        "DePIN infrastructure"
    ]

    results = embed_batch.remote(test_batch)
    print(f"✅ Generated {len(results)} embeddings")
    for i, text in enumerate(test_batch):
        print(f"  - '{text}': {len(results[i])}D")

"""
Simple Modal deployment for Instructor-XL embeddings
Following Modal's latest documentation
"""

import modal

app = modal.App("podinsight-embeddings")

# Create image with our dependencies
image = modal.Image.debian_slim().pip_install(
    "sentence-transformers",
    "torch",
    "numpy"
)

@app.function(
    image=image,
    gpu="T4",
    timeout=600,
)
def generate_embedding(text: str):
    """Generate 768D embedding for text using Instructor-XL"""
    from sentence_transformers import SentenceTransformer

    # This will download the model on first run
    model = SentenceTransformer('hkunlp/instructor-xl')
    instruction = "Represent the venture capital podcast discussion:"

    # Generate embedding
    embedding = model.encode([[instruction, text]])[0]
    return embedding.tolist()


@app.local_entrypoint()
def main():
    """Test the function locally"""
    # Test with a sample query
    test_text = "What are the latest trends in AI venture capital?"
    print(f"Testing with: {test_text}")

    # Call the remote function
    result = generate_embedding.remote(test_text)
    print(f"Generated {len(result)}-dimensional embedding")
    print(f"First 5 values: {result[:5]}")


if __name__ == "__main__":
    # Run locally for testing
    with app.run():
        result = generate_embedding.remote("test")
        print(f"Success! Embedding dimension: {len(result)}")

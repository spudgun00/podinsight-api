import modal
from typing import List, Dict
import json

app = modal.App("podinsight-embeddings-api")

# Create image with ML dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "sentence-transformers==2.7.0",
    "torch>=2.0.0",
    "numpy",
    "fastapi",
    "pydantic"
)

@app.function(
    image=image,
    gpu="T4",
    scaledown_window=300,  # Keep warm for 5 mins
    timeout=600,
)
@modal.web_endpoint(method="POST")
def embed_text(request: Dict) -> Dict:
    """Web endpoint for generating 768D embeddings"""
    from sentence_transformers import SentenceTransformer

    # Extract text from request
    text = request.get("text", "")
    if not text:
        return {"error": "No text provided"}

    print(f"Loading Instructor-XL model...")
    model = SentenceTransformer('hkunlp/instructor-xl')
    instruction = "Represent the venture capital podcast discussion:"

    print(f"Generating embedding for: {text[:50]}...")
    embedding = model.encode([[instruction, text]])[0]

    return {
        "embedding": embedding.tolist(),
        "dimension": len(embedding),
        "model": "instructor-xl"
    }


@app.function(
    image=image,
    gpu="T4",
    scaledown_window=300,
    timeout=600,
)
@modal.web_endpoint(method="POST")
def embed_batch(request: Dict) -> Dict:
    """Web endpoint for batch embeddings"""
    from sentence_transformers import SentenceTransformer

    texts = request.get("texts", [])
    if not texts:
        return {"error": "No texts provided"}

    print(f"Loading model for batch of {len(texts)} texts...")
    model = SentenceTransformer('hkunlp/instructor-xl')
    instruction = "Represent the venture capital podcast discussion:"

    # Format texts with instruction
    formatted_texts = [[instruction, text] for text in texts]
    embeddings = model.encode(formatted_texts)

    return {
        "embeddings": [emb.tolist() for emb in embeddings],
        "count": len(embeddings),
        "dimension": len(embeddings[0]) if embeddings else 0,
        "model": "instructor-xl"
    }


@app.local_entrypoint()
def test():
    """Test the endpoints"""
    import requests

    # Wait for deployment
    print("Deploy this app first with: modal deploy modal_instructor_web.py")
    print("Then find your endpoint URL in the Modal dashboard")
    print("It will be something like:")
    print("https://podinsighthq--podinsight-embeddings-api-embed-text.modal.run")

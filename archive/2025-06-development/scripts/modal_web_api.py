import modal
import json

app = modal.App("podinsight-embeddings-web")

# Create image with dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "sentence-transformers==2.7.0",
    "torch>=2.0.0"
)

@app.function(image=image, gpu="T4")
@modal.web_endpoint(method="POST")
def embed_text(data: dict):
    """HTTP endpoint for text embeddings"""
    from sentence_transformers import SentenceTransformer

    # Parse request
    text = data.get("text", "")
    if not text:
        return {"error": "No text provided"}

    # Load model and generate embedding
    model = SentenceTransformer('hkunlp/instructor-xl')
    instruction = "Represent the venture capital podcast discussion:"
    embedding = model.encode([[instruction, text]])[0]

    return {"embedding": embedding.tolist()}


# Test locally
if __name__ == "__main__":
    with app.run():
        # This will print the URL after deployment
        print("Deploy with: modal deploy modal_web_api.py")

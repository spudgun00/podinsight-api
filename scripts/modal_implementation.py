"""
Modal.com implementation for Instructor-XL embeddings
Deploys the 768D model as a serverless function
"""

import modal
from typing import List
import numpy as np

# Create Modal app
app = modal.App("podinsight-embeddings")

# Define the image with dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "sentence-transformers==2.7.0",
    "InstructorEmbedding==1.0.1",
    "torch>=2.0.0",
    "numpy"
)

# Create a volume for model caching
volume = modal.SharedVolume().persist("instructor-xl-cache")

@app.cls(
    image=image,
    gpu="T4",  # Use GPU for faster inference
    volumes={"/cache": volume},
    container_idle_timeout=300,  # Keep warm for 5 minutes
)
class InstructorXLEmbedder:
    def __enter__(self):
        """Load the model once when container starts"""
        import os
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/cache"
        
        from sentence_transformers import SentenceTransformer
        print("Loading Instructor-XL model...")
        self.model = SentenceTransformer('hkunlp/instructor-xl')
        self.instruction = "Represent the venture capital podcast discussion:"
        print("Model loaded successfully!")
    
    @modal.method()
    def embed_text(self, text: str) -> List[float]:
        """Generate 768D embedding for a single text"""
        embedding = self.model.encode([[self.instruction, text]])[0]
        return embedding.tolist()
    
    @modal.method()
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        formatted_texts = [[self.instruction, text] for text in texts]
        embeddings = self.model.encode(formatted_texts)
        return [emb.tolist() for emb in embeddings]


# Deployment instructions:
"""
1. Install Modal CLI:
   pip install modal

2. Authenticate:
   modal token new

3. Deploy this function:
   modal deploy modal_implementation.py

4. Get your function URL:
   modal app list

5. Update your API to call Modal instead of local model
"""

# Example client code for your API:
"""
import requests

MODAL_FUNCTION_URL = "https://your-app-name--embed-text.modal.run"

async def generate_embedding_768d(text: str) -> List[float]:
    response = requests.post(
        MODAL_FUNCTION_URL,
        json={"text": text},
        headers={"Authorization": f"Bearer {MODAL_TOKEN}"}
    )
    return response.json()["embedding"]
"""
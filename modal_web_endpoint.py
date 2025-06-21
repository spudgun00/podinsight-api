from modal import App, Image, asgi_app
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

# Create Modal app
app = App("podinsight-embeddings-api")

# Create image with dependencies
image = Image.debian_slim(python_version="3.11").pip_install(
    "sentence-transformers==2.7.0",
    "torch>=2.0.0",
    "fastapi",
    "pydantic"
)

# Create FastAPI instance
web_app = FastAPI()

# Request/Response models
class EmbedRequest(BaseModel):
    text: str

class EmbedResponse(BaseModel):
    embedding: List[float]
    dimension: int
    model: str

class BatchEmbedRequest(BaseModel):
    texts: List[str]

class BatchEmbedResponse(BaseModel):
    embeddings: List[List[float]]
    count: int
    dimension: int
    model: str

# Global model instance
model = None
instruction = "Represent the venture capital podcast discussion:"

@web_app.on_event("startup")
async def load_model():
    """Load model on startup"""
    global model
    from sentence_transformers import SentenceTransformer
    print("Loading Instructor-XL model...")
    model = SentenceTransformer('hkunlp/instructor-xl')
    print("Model loaded successfully!")

@web_app.post("/embed", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    """Generate embedding for single text"""
    global model
    
    if model is None:
        return {"error": "Model not loaded"}
    
    # Generate embedding
    embedding = model.encode([[instruction, request.text]])[0]
    
    return EmbedResponse(
        embedding=embedding.tolist(),
        dimension=len(embedding),
        model="instructor-xl"
    )

@web_app.post("/embed_batch", response_model=BatchEmbedResponse)
async def embed_batch(request: BatchEmbedRequest):
    """Generate embeddings for multiple texts"""
    global model
    
    if model is None:
        return {"error": "Model not loaded"}
    
    # Format texts with instruction
    formatted_texts = [[instruction, text] for text in request.texts]
    embeddings = model.encode(formatted_texts)
    
    return BatchEmbedResponse(
        embeddings=[emb.tolist() for emb in embeddings],
        count=len(embeddings),
        dimension=len(embeddings[0]) if embeddings.size else 0,
        model="instructor-xl"
    )

@web_app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model": "instructor-xl"
    }

# Create Modal function
@app.function(
    image=image,
    gpu="T4",
    container_idle_timeout=300,
)
@asgi_app()
def fastapi_app():
    return web_app
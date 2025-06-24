"""
Optimized Modal.com endpoint for PodInsight embeddings
Fixes the 150-second cold start issue with GPU, snapshots, and volume caching
Based on ChatGPT's analysis and Modal best practices
"""

import modal
import torch
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import time

# Create Modal app with optimized configuration
app = modal.App("podinsight-embeddings-optimized")

# Build image with CUDA-enabled PyTorch
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.2.2+cu118",
        "sentence-transformers==2.7.0",
        "instructor",
        "fastapi",
        "pydantic",
        extra_index_url="https://download.pytorch.org/whl/cu118"
    )
)

# Create persistent volume for model weights
volume = modal.Volume.from_name("podinsight-hf-cache", create_if_missing=True)

# FastAPI instance for HTTP endpoints
web_app = FastAPI()

# Request/Response models
class EmbedRequest(BaseModel):
    text: str

class EmbedResponse(BaseModel):
    embedding: List[float]
    dimension: int
    model: str
    gpu_available: bool
    inference_time_ms: float

class BatchEmbedRequest(BaseModel):
    texts: List[str]

class BatchEmbedResponse(BaseModel):
    embeddings: List[List[float]]
    count: int
    dimension: int
    model: str
    gpu_available: bool
    inference_time_ms: float

# Embedding instruction for business context
INSTRUCTION = "Represent the venture capital podcast discussion:"

@app.cls(
    image=image,
    gpu="A10G",  # Explicitly request GPU (can use "T4" to halve cost)
    volumes={"/root/.cache/huggingface": volume},  # Persist model weights
    min_containers=0,  # Allow scale to zero
    max_containers=10,  # Cap for cost control
    scaledown_window=600,  # Stay warm for 10 minutes after last request
    enable_memory_snapshot=True,  # Enable snapshots for 3-4x faster cold starts
    container_idle_timeout=600,  # Match scaledown window
)
class EmbedderOptimized:
    """Optimized embedder with GPU support and memory snapshots"""
    
    @modal.enter(snap=True)
    def load_model_to_cpu(self):
        """Load model to CPU memory (runs before snapshot)"""
        print("🔄 Loading Instructor-XL model to CPU...")
        start = time.time()
        
        # Load to CPU first for snapshot
        self.model = SentenceTransformer('hkunlp/instructor-xl', device='cpu')
        
        elapsed = time.time() - start
        print(f"✅ Model loaded to CPU in {elapsed:.2f}s")
    
    @modal.enter(snap=False)
    def move_model_to_gpu(self):
        """Move model to GPU after snapshot restore (runs on each container start)"""
        print("🚀 Moving model to GPU...")
        start = time.time()
        
        # Check GPU availability
        self.gpu_available = torch.cuda.is_available()
        print(f"🖥️  GPU available: {self.gpu_available}")
        
        if self.gpu_available:
            # Move model to GPU
            self.model.to('cuda')
            # Warm up GPU with a dummy inference
            _ = self.model.encode([[INSTRUCTION, "warmup"]], convert_to_tensor=True)
            print(f"✅ Model moved to GPU: {torch.cuda.get_device_name(0)}")
        else:
            print("⚠️  WARNING: No GPU available, using CPU (will be slow)")
        
        elapsed = time.time() - start
        print(f"✅ GPU setup complete in {elapsed:.2f}s")
    
    @modal.method()
    def embed_single(self, text: str) -> dict:
        """Generate embedding for single text with timing"""
        start = time.time()
        
        # Format with instruction
        formatted_input = [[INSTRUCTION, text]]
        
        # Generate embedding
        with torch.cuda.amp.autocast(enabled=self.gpu_available):
            embedding = self.model.encode(
                formatted_input,
                normalize_embeddings=True,
                convert_to_tensor=False
            )[0]
        
        inference_time = (time.time() - start) * 1000  # ms
        
        return {
            "embedding": embedding.tolist(),
            "dimension": len(embedding),
            "model": "instructor-xl",
            "gpu_available": self.gpu_available,
            "inference_time_ms": round(inference_time, 2)
        }
    
    @modal.method()
    def embed_batch(self, texts: List[str]) -> dict:
        """Generate embeddings for multiple texts with timing"""
        start = time.time()
        
        # Format with instruction
        formatted_inputs = [[INSTRUCTION, text] for text in texts]
        
        # Generate embeddings
        with torch.cuda.amp.autocast(enabled=self.gpu_available):
            embeddings = self.model.encode(
                formatted_inputs,
                normalize_embeddings=True,
                convert_to_tensor=False,
                batch_size=32  # Optimize for GPU memory
            )
        
        inference_time = (time.time() - start) * 1000  # ms
        
        return {
            "embeddings": [emb.tolist() for emb in embeddings],
            "count": len(embeddings),
            "dimension": len(embeddings[0]) if embeddings.size else 0,
            "model": "instructor-xl",
            "gpu_available": self.gpu_available,
            "inference_time_ms": round(inference_time, 2)
        }
    
    @modal.web_endpoint(method="POST", path="/embed")
    def web_embed_single(self, request: EmbedRequest) -> EmbedResponse:
        """HTTP endpoint for single embedding"""
        result = self.embed_single(request.text)
        return EmbedResponse(**result)
    
    @modal.web_endpoint(method="POST", path="/embed_batch")
    def web_embed_batch(self, request: BatchEmbedRequest) -> BatchEmbedResponse:
        """HTTP endpoint for batch embeddings"""
        result = self.embed_batch(request.texts)
        return BatchEmbedResponse(**result)
    
    @modal.web_endpoint(method="GET", path="/health")
    def health_check(self) -> dict:
        """Health check endpoint with GPU status"""
        return {
            "status": "healthy",
            "model": "instructor-xl",
            "gpu_available": self.gpu_available,
            "gpu_name": torch.cuda.get_device_name(0) if self.gpu_available else None,
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda if self.gpu_available else None,
            "snapshot_enabled": True,
            "scaledown_window": 600,
            "expected_cold_start": "~7 seconds",
            "expected_warm_latency": "<200ms"
        }
    
    @modal.web_endpoint(method="GET", path="/warm")
    def warm_endpoint(self) -> dict:
        """Lightweight endpoint to keep container warm"""
        return {"status": "warm", "timestamp": time.time()}

# Create the optimized embedder instance
embedder = EmbedderOptimized()

# Also create a standalone web function for flexibility
@app.function(
    image=image,
    gpu="A10G",
    volumes={"/root/.cache/huggingface": volume},
    scaledown_window=600,
    enable_memory_snapshot=True,
    container_idle_timeout=600,
)
@modal.asgi_app()
def fastapi_app():
    """Alternative FastAPI deployment option"""
    return web_app

# Add routes to FastAPI app
@web_app.post("/embed", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    """Generate embedding for single text"""
    # This would need to instantiate the embedder
    # For now, this is a placeholder for the alternative deployment
    return {"error": "Use the class-based endpoints instead"}

@web_app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "deployment": "fastapi_app",
        "gpu_expected": "A10G",
        "snapshot_enabled": True
    }

if __name__ == "__main__":
    # Deploy with: modal deploy scripts/modal_web_endpoint_optimized.py
    print("Deploy this with: modal deploy scripts/modal_web_endpoint_optimized.py")
    print("\nExpected performance:")
    print("- Cold start: ~7 seconds (down from 150s)")
    print("- Warm requests: <200ms")
    print("- Cost: ~$6.40/month for 100 bursts/day")
    print("\nThe endpoint will be available at:")
    print("https://[your-modal-subdomain]--podinsight-embeddings-optimized-embedder-web-embed-single.modal.run")
"""
Simple Modal.com endpoint for PodInsight embeddings
Simplified version to fix the endpoint issues
"""

import modal
from typing import List
import time

# These imports only work inside Modal containers
try:
    import torch
    from sentence_transformers import SentenceTransformer
except ImportError:
    # Not available locally, will be available in Modal container
    pass

# Create Modal app
app = modal.App("podinsight-embeddings-simple")

# Build image with updated dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "numpy>=1.26.0,<2.0",
        "torch==2.7.1+cu121",  # Fixed CUDA version pin
        "sentence-transformers==2.7.0",  # Tested version
        "fastapi",
        "pydantic",
        extra_index_url="https://download.pytorch.org/whl/cu121"
    )
)

# Create persistent volume for model weights
volume = modal.Volume.from_name("podinsight-hf-cache", create_if_missing=True)

# Embedding instruction for business context
INSTRUCTION = "Represent the venture capital podcast discussion:"

# Global model cache to avoid reloading
MODEL = None

def get_model():
    """Get or load the model (cached globally)"""
    global MODEL
    if MODEL is None:
        print("📥 Loading model to cache...")
        start = time.time()
        MODEL = SentenceTransformer('hkunlp/instructor-xl')
        
        # Move to GPU if available
        if torch.cuda.is_available():
            print(f"🖥️  Moving model to GPU: {torch.cuda.get_device_name(0)}")
            MODEL.to('cuda')
            # Warm up with dummy inference
            _ = MODEL.encode([["warmup", "dummy"]], convert_to_tensor=False)
        else:
            print("⚠️  No GPU available, using CPU")
            
        load_time = time.time() - start
        print(f"✅ Model loaded and cached in {load_time:.2f}s")
    
    return MODEL

@app.function(
    image=image,
    gpu="A10G",
    volumes={"/root/.cache/huggingface": volume},
    scaledown_window=600,
    enable_memory_snapshot=True,  # Re-enabled - Modal fixed the bug
    max_containers=10,  # Concurrency guard-rail
)
def generate_embedding(text: str) -> dict:
    """Generate embedding for a single text"""
    print(f"🔄 Generating embedding for: {text[:50]}...")
    start = time.time()
    
    try:
        # Get cached model (fast for warm requests)
        model_start = time.time()
        model = get_model()
        model_load_time = time.time() - model_start
        
        # Check GPU status
        gpu_available = torch.cuda.is_available()
        
        # Generate embedding
        embed_start = time.time()
        formatted_input = [[INSTRUCTION, text]]
        
        with torch.cuda.amp.autocast(enabled=gpu_available):
            embedding = model.encode(
                formatted_input,
                normalize_embeddings=True,
                convert_to_tensor=False
            )[0]
        
        embed_time = time.time() - embed_start
        total_time = time.time() - start
        
        print(f"✅ Embedding generated in {embed_time:.2f}s (total: {total_time:.2f}s)")
        
        return {
            "embedding": embedding.tolist(),
            "dimension": len(embedding),
            "model": "instructor-xl",
            "gpu_available": gpu_available,
            "inference_time_ms": round(embed_time * 1000, 2),
            "total_time_ms": round(total_time * 1000, 2),
            "model_load_time_ms": round(model_load_time * 1000, 2)
        }
        
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return {
            "error": str(e),
            "embedding": None,
            "dimension": 0,
            "model": "instructor-xl",
            "gpu_available": False,
            "inference_time_ms": 0
        }

@app.function(
    image=image,
    gpu="A10G",
    volumes={"/root/.cache/huggingface": volume},
    scaledown_window=600,
)
def health_check() -> dict:
    """Simple health check"""
    try:
        gpu_available = torch.cuda.is_available()
        return {
            "status": "healthy",
            "model": "instructor-xl",
            "gpu_available": gpu_available,
            "gpu_name": torch.cuda.get_device_name(0) if gpu_available else None,
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda if gpu_available else None,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    print("Deploy this with: modal deploy scripts/modal_web_endpoint_simple.py")
    print("\nThis is a simplified version for debugging")
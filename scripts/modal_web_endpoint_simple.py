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
        "torch>=2.6.0",
        "sentence-transformers==2.7.0",
        "fastapi",
        "pydantic",
    )
)

# Create persistent volume for model weights
volume = modal.Volume.from_name("podinsight-hf-cache", create_if_missing=True)

# Embedding instruction for business context
INSTRUCTION = "Represent the venture capital podcast discussion:"

@app.function(
    image=image,
    gpu="A10G",
    volumes={"/root/.cache/huggingface": volume},
    scaledown_window=600,
    enable_memory_snapshot=False,  # Disable for simplicity
)
def generate_embedding(text: str) -> dict:
    """Generate embedding for a single text"""
    print(f"🔄 Generating embedding for: {text[:50]}...")
    start = time.time()
    
    try:
        # Load model (will be cached after first load)
        print("📥 Loading model...")
        model_start = time.time()
        model = SentenceTransformer('hkunlp/instructor-xl')
        model_load_time = time.time() - model_start
        print(f"✅ Model loaded in {model_load_time:.2f}s")
        
        # Check GPU
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            print(f"🖥️  Using GPU: {torch.cuda.get_device_name(0)}")
            model.to('cuda')
        else:
            print("⚠️  Using CPU")
        
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
"""
Simple Modal.com endpoint for PodInsight embeddings
Simplified version to fix the endpoint issues
"""

import modal
from typing import List, Dict
import time
from pydantic import BaseModel

# These imports only work inside Modal containers
try:
    import torch
    import numpy as np
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
        "torch==2.6.0",  # Updated to address CVE-2025-32434 security vulnerability
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

# Request model for web endpoint
class EmbeddingRequest(BaseModel):
    text: str

def get_model():
    """Get or load the model (cached globally)"""
    global MODEL
    if MODEL is None:
        print("📥 Loading model to cache...")
        start = time.time()
        
        # Load model - try without trust_remote_code first
        try:
            MODEL = SentenceTransformer('hkunlp/instructor-xl')
            print("✅ Loaded without trust_remote_code")
        except Exception as e:
            print(f"⚠️ Loading without trust_remote_code failed: {e}")
            MODEL = SentenceTransformer('hkunlp/instructor-xl', trust_remote_code=True)
            print("✅ Loaded with trust_remote_code")
        
        # Move to GPU if available
        if torch.cuda.is_available():
            print(f"🖥️  Moving model to GPU: {torch.cuda.get_device_name(0)}")
            MODEL.to('cuda')
            
            # Pre-compile CUDA kernels with dummy encode
            print("🔥 Pre-compiling CUDA kernels...")
            try:
                # Do a real encode to trigger kernel compilation
                dummy_texts = [
                    ["Represent the sentence:", "warmup test"],
                    ["Represent the sentence:", "hello world"]
                ]
                _ = MODEL.encode(dummy_texts, convert_to_tensor=False)
                print("✅ CUDA kernels pre-compiled")
            except Exception as e:
                print(f"⚠️  Warmup failed: {e}")
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
    # min_containers=1,  # Uncomment to keep 1 container always warm (zero cold boots)
)
@modal.fastapi_endpoint(method="POST")
def generate_embedding(request: EmbeddingRequest) -> Dict:
    """Generate embedding for a single text"""
    return _generate_embedding(request.text)

def _generate_embedding(text: str) -> Dict:
    """Internal function to generate embedding"""
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
        
        # Try both formats to see which works
        try:
            # Format 1: Instructor format
            formatted_input = [[INSTRUCTION, text]]
            
            # Try without autocast first
            embedding = model.encode(
                formatted_input,
                normalize_embeddings=True,
                convert_to_tensor=False,
                show_progress_bar=False
            )[0]
            
            print(f"   ✅ Format 1 succeeded without autocast")
        except Exception as e:
            print(f"   ❌ Format 1 failed: {e}")
            try:
                # Format 2: Simple text
                embedding = model.encode(
                    text,
                    normalize_embeddings=True,
                    convert_to_tensor=False,
                    show_progress_bar=False
                )
                print(f"   ✅ Format 2 succeeded")
            except Exception as e2:
                print(f"   ❌ Format 2 also failed: {e2}")
                raise e2
        
        embed_time = time.time() - embed_start
        total_time = time.time() - start
        
        print(f"✅ Embedding generated in {embed_time:.2f}s (total: {total_time:.2f}s)")
        
        # Debug: Check embedding
        print(f"   Embedding type: {type(embedding)}")
        print(f"   Embedding shape: {embedding.shape if hasattr(embedding, 'shape') else 'N/A'}")
        
        # Convert to list properly
        if isinstance(embedding, np.ndarray):
            embedding_list = embedding.tolist()
        elif hasattr(embedding, 'cpu'):  # PyTorch tensor
            embedding_list = embedding.cpu().numpy().tolist()
        else:
            embedding_list = list(embedding)
        
        print(f"   First 5 values: {embedding_list[:5] if len(embedding_list) > 5 else embedding_list}")
        print(f"   Valid embedding: {isinstance(embedding_list[0], (int, float)) if embedding_list else False}")
        
        return {
            "embedding": embedding_list,
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
@modal.fastapi_endpoint(method="GET")
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

@app.function(
    image=image,
    gpu="A10G",
    volumes={"/root/.cache/huggingface": volume},
    scaledown_window=600,
    enable_memory_snapshot=True,
)
def test_embedding(text: str = "test embedding generation") -> None:
    """Test function for modal run"""
    result = _generate_embedding(text)
    print(f"\n📊 Test Results:")
    print(f"   Embedding dimension: {result.get('dimension', 0)}")
    print(f"   GPU available: {result.get('gpu_available', False)}")
    print(f"   Inference time: {result.get('inference_time_ms', 0)}ms")
    print(f"   Total time: {result.get('total_time_ms', 0)}ms")
    print(f"   Model load time: {result.get('model_load_time_ms', 0)}ms")

if __name__ == "__main__":
    print("Deploy this with: modal deploy scripts/modal_web_endpoint_simple.py")
    print("\nAfter deployment, test with:")
    print("  modal run scripts/modal_web_endpoint_simple.py::test_embedding --text 'your text here'")
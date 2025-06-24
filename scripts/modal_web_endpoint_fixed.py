"""
Fixed Modal.com endpoint for PodInsight embeddings with proper memory snapshots
Implements all advisor recommendations to achieve 4-6s cold starts
"""

import modal
from typing import Dict
import time
import logging
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Modal app
app = modal.App("podinsight-embeddings-fixed")

# Build optimized image with all dependencies baked in
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "numpy==1.26.4",
        "torch==2.6.0",
        "sentence-transformers==2.7.0",
        "fastapi",
        "pydantic",
        extra_index_url="https://download.pytorch.org/whl/cu121"
    )
    # Install system dependencies at build time
    .run_commands("apt-get update && apt-get install -y libgomp1")
    # Pre-download the model weights into the image
    .run_commands(
        "python -c \"from sentence_transformers import SentenceTransformer; "
        "model = SentenceTransformer('hkunlp/instructor-xl'); "
        "print('Model downloaded successfully')\""
    )
)

# Embedding instruction for business context
INSTRUCTION = "Represent the venture capital podcast discussion:"

# Request model for web endpoint
class EmbeddingRequest(BaseModel):
    text: str

@app.cls(
    image=image,
    gpu="A10G",
    scaledown_window=600,
    enable_memory_snapshot=True,  # Critical for cold start optimization
    max_containers=10,
)
class EmbeddingModel:
    """Model class with proper snapshot support"""
    
    @modal.enter(snap=True)  # This is the key - snap=True enables memory snapshots
    def load_model(self):
        """Load model in snapshot-enabled context"""
        logger.info("🔄 Loading model in snapshot context...")
        start = time.time()
        
        # Import here to ensure it's available
        import torch
        import numpy as np
        from sentence_transformers import SentenceTransformer
        
        # Load model directly (weights are already in the image)
        self.model = SentenceTransformer('hkunlp/instructor-xl')
        logger.info("✅ Model loaded from cache")
        
        # Move to GPU - this MUST happen in the snapshot context
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"🖥️  Moving model to GPU: {gpu_name}")
            self.model.to('cuda')
            
            # Warm up GPU
            warmup_text = [["Represent the sentence:", "warmup test"]]
            _ = self.model.encode(warmup_text, convert_to_tensor=False)
            logger.info("✅ GPU warmup complete")
        else:
            logger.warning("⚠️  No GPU available, using CPU")
        
        load_time = time.time() - start
        logger.info(f"✅ Model loaded and moved to GPU in {load_time:.2f}s")
        
        # Store these for later use
        self.torch = torch
        self.np = np
    
    @modal.fastapi_endpoint(method="POST")
    def generate_embedding(self, request: EmbeddingRequest) -> Dict:
        """Generate embedding for a single text"""
        return self._generate_embedding(request.text)
    
    def _generate_embedding(self, text: str) -> Dict:
        """Internal function to generate embedding"""
        start = time.time()
        
        # Log cold start status
        is_cold = getattr(modal, 'is_cold_start', lambda: None)()
        if is_cold is not None:
            logger.info(f"cold={is_cold}, dur={time.time()-start:.3f}s")
        
        try:
            # Check GPU status
            gpu_available = self.torch.cuda.is_available()
            
            # Generate embedding
            embed_start = time.time()
            
            # Use instructor format
            formatted_input = [[INSTRUCTION, text]]
            
            embedding = self.model.encode(
                formatted_input,
                normalize_embeddings=True,
                convert_to_tensor=False,
                show_progress_bar=False
            )[0]
            
            embed_time = time.time() - embed_start
            total_time = time.time() - start
            
            # Convert to list
            if isinstance(embedding, self.np.ndarray):
                embedding_list = embedding.tolist()
            elif hasattr(embedding, 'cpu'):  # PyTorch tensor
                embedding_list = embedding.cpu().numpy().tolist()
            else:
                embedding_list = list(embedding)
            
            # Log performance
            logger.info(f"✅ Embedding generated - inference: {embed_time*1000:.1f}ms, total: {total_time*1000:.1f}ms")
            
            return {
                "embedding": embedding_list,
                "dimension": len(embedding),
                "model": "instructor-xl",
                "gpu_available": gpu_available,
                "inference_time_ms": round(embed_time * 1000, 2),
                "total_time_ms": round(total_time * 1000, 2),
                "model_load_time_ms": 0.0,  # Model is preloaded
                "is_cold_start": is_cold
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}")
            return {
                "error": str(e),
                "embedding": None,
                "dimension": 0,
                "model": "instructor-xl",
                "gpu_available": False,
                "inference_time_ms": 0
            }
    
    @modal.method()
    def is_snapshot(self) -> bool:
        """Check if container was restored from snapshot"""
        try:
            return modal.current_snapshot_is_restored()
        except:
            # Fallback if function doesn't exist
            return None
    
    @modal.fastapi_endpoint(method="GET")
    def health_check(self) -> dict:
        """Simple health check"""
        try:
            gpu_available = self.torch.cuda.is_available()
            return {
                "status": "healthy",
                "model": "instructor-xl",
                "gpu_available": gpu_available,
                "gpu_name": self.torch.cuda.get_device_name(0) if gpu_available else None,
                "torch_version": self.torch.__version__,
                "cuda_version": self.torch.version.cuda if gpu_available else None,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

@app.function(
    image=image,
    gpu="A10G",
    scaledown_window=600,
    enable_memory_snapshot=True,
)
def test_embedding(text: str = "test embedding generation") -> None:
    """Test function for modal run"""
    import torch
    
    model = EmbeddingModel()
    model.torch = torch
    model.load_model()
    result = model._generate_embedding(text)
    
    print(f"\n📊 Test Results:")
    print(f"   Embedding dimension: {result.get('dimension', 0)}")
    print(f"   GPU available: {result.get('gpu_available', False)}")
    print(f"   Inference time: {result.get('inference_time_ms', 0)}ms")
    print(f"   Total time: {result.get('total_time_ms', 0)}ms")
    print(f"   Cold start: {result.get('is_cold_start', 'unknown')}")

if __name__ == "__main__":
    print("Deploy this with: modal deploy scripts/modal_web_endpoint_fixed.py")
    print("\nAfter deployment:")
    print("1. Check Modal logs for 'Creating memory snapshot...' on first deploy")
    print("2. After container scales down, next request should show 'Using memory snapshot...'")
    print("3. Cold start should be 4-6s instead of 26s")
    print("\nTest with:")
    print("  modal run scripts/modal_web_endpoint_fixed.py::test_embedding --text 'your text here'")
"""
Minimal test to verify Modal memory snapshots are working
Deploy this to test snapshot functionality
"""

import modal
import time

app = modal.App("snapshot-test")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.6.0",
        "sentence-transformers==2.7.0",
        "numpy==1.26.4",
        extra_index_url="https://download.pytorch.org/whl/cu121"
    )
    .run_commands(
        # Pre-download weights once at build time
        "python -c \"from sentence_transformers import SentenceTransformer; "
        "model = SentenceTransformer('hkunlp/instructor-xl'); "
        "print('Model downloaded successfully')\""
    )
)

@app.cls(
    image=image,
    gpu="A10G",
    enable_memory_snapshot=True,
    scaledown_window=300,  # 5 minutes for faster testing
)
class SnapshotTest:
    @modal.enter(snap=True)
    def load_model(self):
        """This should trigger snapshot creation"""
        print("🔄 Loading in snapshot context...")
        start = time.time()
        
        # Check cold start
        if hasattr(modal, 'is_cold_start'):
            print(f"Cold start: {modal.is_cold_start()}")
        
        # Simulate heavy model loading
        from sentence_transformers import SentenceTransformer
        import torch
        
        print("Loading model...")
        self.model = SentenceTransformer('hkunlp/instructor-xl')
        
        if torch.cuda.is_available():
            print(f"Moving to GPU: {torch.cuda.get_device_name(0)}")
            self.model.to('cuda')
        
        elapsed = time.time() - start
        print(f"✅ Model loaded in {elapsed:.2f}s")
        print("📸 Snapshot should be created after this method completes")
    
    @modal.method()
    def test(self):
        """Test method"""
        import torch
        start = time.time()
        
        # Log cold start status
        is_cold = getattr(modal, 'is_cold_start', lambda: False)()
        print(f"Test method - cold start: {is_cold}")
        
        # Verify GPU usage
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
            print(f"GPU: {gpu_name}")
            print(f"Model device: {next(self.model.parameters()).device}")
        else:
            print("WARNING: No GPU available!")
        
        # Time just the encoding
        encode_start = time.time()
        embedding = self.model.encode("test", convert_to_tensor=False)
        encode_time = time.time() - encode_start
        
        elapsed = time.time() - start
        print(f"Encoding time: {encode_time:.3f}s")
        print(f"Total time: {elapsed:.3f}s")
        
        return {
            "cold_start": is_cold,
            "time_ms": elapsed * 1000,
            "encode_time_ms": encode_time * 1000,
            "embedding_dim": len(embedding),
            "gpu_available": gpu_available
        }
    
    @modal.method()
    def is_snapshot(self):
        """Check if container was restored from snapshot"""
        try:
            return modal.current_snapshot_is_restored()
        except:
            # Fallback if function doesn't exist
            return None

@app.function(schedule=modal.Cron("*/12 * * * *"))
def keep_warm():
    """Keep container warm every 12 minutes (allows true cold starts with 10 min scaledown)"""
    model = SnapshotTest()
    result = model.test.remote()  # Fix: add .remote() for proper Modal call
    print(f"Keep-warm result: {result}")
    
    # Also check snapshot status
    try:
        is_snapshot = model.is_snapshot.remote()
        print(f"Container from snapshot: {is_snapshot}")
    except:
        print("Could not check snapshot status")

if __name__ == "__main__":
    print("Deploy with: modal deploy scripts/modal_snapshot_test.py")
    print("Run test with: modal run scripts/modal_snapshot_test.py::SnapshotTest.test")
    print("Check logs for snapshot messages")
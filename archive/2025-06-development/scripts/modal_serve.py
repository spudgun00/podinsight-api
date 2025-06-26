import modal

app = modal.App("podinsight-embeddings-serve")

image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "sentence-transformers==2.7.0",
    "torch>=2.0.0"
)

with image.imports():
    from sentence_transformers import SentenceTransformer

# Pre-load the model
@app.cls(image=image, gpu="T4")
class Model:
    model: SentenceTransformer

    @modal.enter()
    def setup(self):
        self.model = SentenceTransformer('hkunlp/instructor-xl')
        self.instruction = "Represent the venture capital podcast discussion:"

    @modal.method()
    def generate_embedding(self, text: str):
        embedding = self.model.encode([[self.instruction, text]])[0]
        return embedding.tolist()


@app.local_entrypoint()
def main():
    model = Model()
    result = model.generate_embedding.remote("test query")
    print(f"Embedding dimension: {len(result)}")
    print("\nTo use from your API:")
    print("1. Deploy: modal deploy modal_serve.py")
    print("2. Then call from Python:")
    print("   model = modal.Cls.lookup('podinsight-embeddings-serve', 'Model')")
    print("   embedding = model.generate_embedding.remote('your text')")

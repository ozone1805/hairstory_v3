import os
import json
import openai
from tqdm import tqdm
from pinecone import Pinecone, ServerlessSpec

# Load environment variables
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")  # This is the region, e.g., 'us-east-1'
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not PINECONE_API_KEY or not PINECONE_ENV or not OPENAI_API_KEY:
    raise ValueError("PINECONE_API_KEY, PINECONE_ENV, and OPENAI_API_KEY must be set as environment variables.")

# Create OpenAI client (new API)
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Pinecone setup (new API)
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "hairstory-products"

# Create index if it doesn't exist
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region=PINECONE_ENV
        )
    )

index = pc.Index(index_name)

# Read product data
with open("data/all_products.json", "r") as f:
    products = json.load(f)

# Helper: get embedding (new OpenAI API)
EMBED_MODEL = "text-embedding-ada-002"
def get_embedding(text):
    response = client.embeddings.create(
        input=[text],
        model=EMBED_MODEL
    )
    return response.data[0].embedding

# Prepare and upsert
vectors = []
for i, product in enumerate(tqdm(products)):
    text = " ".join([
        str(product.get("name") or ""),
        str(product.get("subtitle") or ""),
        str(product.get("details") or ""),
        str(product.get("benefits") or "")
    ])
    embedding = get_embedding(text)
    meta = {
        "name": product.get("name", ""),
        "url": product.get("url", ""),
        "type": product.get("type", ""),
        "subtitle": product.get("subtitle", "")
    }
    vectors.append({
        "id": str(i),
        "values": embedding,
        "metadata": meta
    })
    # Upsert in batches of 50
    if len(vectors) == 50 or i == len(products) - 1:
        index.upsert(vectors)
        vectors = []

print("✅ All products upserted to Pinecone.") 
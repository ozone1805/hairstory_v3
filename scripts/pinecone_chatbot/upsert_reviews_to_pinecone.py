import os
import csv
import logging
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

import openai
from pinecone import Pinecone, ServerlessSpec

load_dotenv()


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")  # e.g., "us-east-1"

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY missing from environment.")
if not PINECONE_API_KEY or not PINECONE_ENV:
    raise ValueError("PINECONE_API_KEY or PINECONE_ENV missing from environment.")

client = openai.OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)

INDEX_NAME = "hairstory-reviews"
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536


def ensure_index(index_name: str) -> None:
    names = pc.list_indexes().names()
    if index_name not in names:
        logger.info("Creating Pinecone index '%s'...", index_name)
        pc.create_index(
            name=index_name,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=PINECONE_ENV),
        )


def build_text(row: Dict[str, Any]) -> str:
    parts: List[str] = []
    title = (row.get("Product Title") or "").strip()
    desc = (row.get("Product Description") or "").strip()
    review_title = (row.get("Review Title") or "").strip()
    content = (row.get("Review Content") or "").strip()
    hair_concerns = (row.get("cf_Default form__Hair Concerns") or "").strip()
    hair_type = (row.get("cf_Default form__Hair Type") or "").strip()
    wash_days = (row.get("cf_Default form__Wash Days") or "").strip()

    if title:
        parts.append(f"Product: {title}")
    if desc:
        parts.append(desc)
    if review_title:
        parts.append(f"Title: {review_title}")
    if content:
        parts.append(content)
    hair_bits = ", ".join([b for b in [hair_concerns, hair_type, wash_days] if b])
    if hair_bits:
        parts.append(f"Hair: {hair_bits}")
    return "\n".join(parts)


def parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def parse_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def upsert_reviews(csv_path: str, limit: Optional[int] = None, batch_size: int = 100) -> None:
    ensure_index(INDEX_NAME)
    index = pc.Index(INDEX_NAME)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        batch_rows: List[Dict[str, Any]] = []
        processed = 0

        def process_batch(rows: List[Dict[str, Any]]) -> None:
            if not rows:
                return
            texts = [build_text(r) for r in rows]
            resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
            embeddings = [d.embedding for d in resp.data]

            vectors = []
            for r, emb in zip(rows, embeddings):
                review_id = r.get("Review ID") or str(processed)
                meta = {
                    "review_id": review_id,
                    "review_content": (r.get("Review Content") or "").strip(),
                    "review_score": parse_int(r.get("Review Score"), 0),
                    "sentiment_score": parse_float(r.get("Sentiment Score"), 0.0),
                    "product_id": (r.get("Product ID") or "").strip(),
                    "product_title": (r.get("Product Title") or "").strip(),
                    "product_title_lower": (r.get("Product Title") or "").strip().lower(),
                    "product_url": (r.get("Product URL") or "").strip(),
                    "hair_concerns": (r.get("cf_Default form__Hair Concerns") or "").strip(),
                    "hair_type": (r.get("cf_Default form__Hair Type") or "").strip(),
                    "wash_days": (r.get("cf_Default form__Wash Days") or "").strip(),
                }
                vectors.append({"id": str(review_id), "values": emb, "metadata": meta})

            index.upsert(vectors)

        for row in reader:
            batch_rows.append(row)
            processed += 1

            if len(batch_rows) >= batch_size:
                logger.info(f"Processing batch {processed//batch_size} ({processed} reviews processed)")
                process_batch(batch_rows)
                batch_rows = []

            if limit is not None and processed >= limit:
                break

        # process leftover
        if batch_rows:
            logger.info(f"Processing final batch ({processed} reviews processed)")
            process_batch(batch_rows)

    logger.info("✅ Upsert completed. Processed %s reviews%s.", processed, f" (limit)" if limit else "")


if __name__ == "__main__":
    # Defaults to your CSV in repo root; override with env var or arguments if needed
    csv_path = os.getenv("REVIEWS_CSV_PATH", "Reviews_export_2025_07_15_19_41_16.600.csv")
    limit_env = os.getenv("UPSERT_LIMIT")
    limit_val: Optional[int] = int(limit_env) if limit_env else None
    
    if limit_val:
        logger.info(f"Processing first {limit_val} reviews...")
    
    upsert_reviews(csv_path=csv_path, limit=limit_val)


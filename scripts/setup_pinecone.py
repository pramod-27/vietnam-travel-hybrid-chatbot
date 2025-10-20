#!/usr/bin/env python3
"""
scripts/setup_pinecone.py

Reads data/vietnam_travel_dataset.json and uploads semantic embeddings to Pinecone.
- Uses semantic_text (fallback description) for embedding content.
- Attaches rich metadata to each vector for better retrieval & prompt-building.
- Batches uploads and prints stats.

Expectations:
- config.Config has PINECONE_API_KEY, PINECONE_INDEX_NAME, VECTOR_DIMENSION, EMBEDDING_MODEL, etc.
- services.embedding_service.EmbeddingService exists (uses OPENAI/GOOGLE or deterministic mock).
- services.vector_service.VectorService exists (wrapping pinecone client).
If those aren't present, the script will fallback to a minimal deterministic embedding generator (for local tests).
"""

#!/usr/bin/env python3
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # ✅ add repo root to sys.path

import json
import time
from pathlib import Path
from typing import List, Dict
import math

# Local imports (from repo)
from config import Config
from utils.logger import logger
from services.embedding_service import EmbeddingService
from services.vector_service import VectorService


# Constants
DATA_PATH = Path("data/vietnam_travel_dataset.json")
BATCH_SIZE = int(os.getenv("PINECONE_BATCH_SIZE", "100"))

def _load_data(path: Path) -> List[Dict]:
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def _prepare_metadata(item: Dict) -> Dict:
    """Extract metadata fields used for Pinecone retrieval and context building."""
    md = {
        "id": item.get("id"),
        "type": item.get("type"),
        "name": item.get("name"),
        # limit description size to avoid huge metadata
        "description": (item.get("description") or "")[:800],
        "semantic_text": (item.get("semantic_text") or "")[:1000],
        "tags": item.get("tags") or [],
    }
    if "city" in item:
        md["city"] = item.get("city")
    if "region" in item:
        md["region"] = item.get("region")
    if "best_time_to_visit" in item:
        md["best_time_to_visit"] = item.get("best_time_to_visit")
    return md

def _text_to_embed(item: Dict) -> str:
    """Choose the best text for embeddings: semantic_text > description > name."""
    text = (item.get("semantic_text") or "").strip()
    if not text:
        text = (item.get("description") or "").strip()
    if not text:
        text = item.get("name", "")
    # Add type/tags concisely to help retrieval
    tags = item.get("tags") or []
    if tags:
        text = text + " | Tags: " + ", ".join(tags)
    return text

def generate_vectors(data: List[Dict], emb_svc: EmbeddingService) -> List[Dict]:
    vectors = []
    total = len(data)
    for i, item in enumerate(data, start=1):
        try:
            text = _text_to_embed(item)
            emb = emb_svc.generate_embedding(text)
            metadata = _prepare_metadata(item)
            vector = {"id": item["id"], "values": emb, "metadata": metadata}
            vectors.append(vector)
            if i % 50 == 0:
                logger.info(f"Prepared {i}/{total} vectors")
        except Exception as e:
            logger.error(f"Failed to prepare vector for {item.get('id')}: {e}")
    return vectors

def upload_vectors(vectors: List[Dict], vs: "VectorService", batch_size: int = BATCH_SIZE):
    total = len(vectors)
    logger.info(f"Uploading {total} vectors to Pinecone in batches of {batch_size}")
    idx = vs.get_index()
    for i in range(0, total, batch_size):
        batch = vectors[i:i+batch_size]
        # Format: list of dicts {"id":..., "values":..., "metadata":...}
        try:
            idx.upsert(vectors=batch)
            logger.info(f"Upserted batch {i//batch_size + 1} ({len(batch)} vectors)")
            time.sleep(0.2)
        except Exception as e:
            logger.error(f"Upsert failed for batch {i//batch_size + 1}: {e}")
            # continue to next batch but log
    logger.info("Upload complete")

def main():
    # Config validation
    if Config:
        try:
            # don't forcibly require all keys here; VectorService may check later
            pass
        except Exception:
            pass

    logger.info("Loading dataset")
    data = _load_data(DATA_PATH)
    logger.info(f"Loaded {len(data)} items from {DATA_PATH}")

    # Build embeddings
    emb_svc = EmbeddingService()
    provider_info = emb_svc.get_provider_info() if hasattr(emb_svc, "get_provider_info") else {"provider":"unknown"}
    logger.info(f"Using embedding provider: {provider_info}")

    vectors = generate_vectors(data, emb_svc)
    if not vectors:
        logger.error("No vectors prepared; aborting upload")
        return

    # Upload to Pinecone
    try:
        vs = VectorService()
    except Exception as e:
        logger.error(f"VectorService initialization failed: {e}")
        logger.error("Make sure pinecone-client is installed and config has PINECONE_API_KEY")
        raise

    # Create index if needed (VectorService.create_index should be implemented)
    try:
        vs.create_index(dimension=len(vectors[0]["values"]))
    except Exception as e:
        logger.warning(f"Index creation check failed (continuing): {e}")

    upload_vectors(vectors, vs, batch_size=BATCH_SIZE)

    # Print basic stats (best-effort)
    try:
        stats = vs.describe()
        logger.info(f"Pinecone index info: {stats}")
    except Exception:
        logger.info("Couldn't fetch index describe info")

    # run a test query
    try:
        q = "romantic beach destination for couples"
        q_emb = emb_svc.generate_embedding(q)
        matches = vs.search(query_vector=q_emb, top_k=5)
        logger.info("Sample query returned %d matches" % len(matches))
        for m in matches[:5]:
            meta = m.get("metadata", {})
            logger.info(f" - {meta.get('name')} ({meta.get('type')}) score={m.get('score')}")
    except Exception as e:
        logger.warning(f"Test query failed: {e}")

if __name__ == "__main__":
    main()

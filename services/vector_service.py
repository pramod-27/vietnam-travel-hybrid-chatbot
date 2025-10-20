# services/vector_service.py
import os, sys, time
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # allow config import

from typing import List, Dict, Optional
from config import Config
from utils.logger import logger

try:
    from pinecone import Pinecone, ServerlessSpec
except ImportError:
    Pinecone = None


class VectorService:
    """Wrapper for Pinecone v2 with safer PowerShell-friendly initialization."""
    def __init__(self):
        if Pinecone is None:
            raise RuntimeError(
                "Pinecone client not installed. Run:\n  pip install pinecone-client==3.1.0"
            )
        if not Config.PINECONE_API_KEY:
            raise RuntimeError("Missing PINECONE_API_KEY in your .env file")

        self.pc = Pinecone(api_key=Config.PINECONE_API_KEY)
        self.index_name = Config.PINECONE_INDEX_NAME
        self.dimension = Config.VECTOR_DIMENSION
        #logger.info(f"VectorService connected. Index={self.index_name}")

    def create_index(self, dimension: Optional[int] = None, force_recreate=False):
        d = dimension or self.dimension
        existing = [i.name for i in self.pc.list_indexes()]
        if self.index_name in existing:
            info = self.pc.describe_index(self.index_name)
            curr_dim = getattr(info, "dimension", None) or info.get("dimension")
            if int(curr_dim) == int(d) and not force_recreate:
                logger.info("Index already exists and matches dimension.")
                return
            logger.info("Recreating index to match dimension...")
            self.pc.delete_index(self.index_name)
            time.sleep(2)

        self.pc.create_index(
            name=self.index_name,
            dimension=d,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=Config.PINECONE_ENVIRONMENT),
        )
        for _ in range(30):
            desc = self.pc.describe_index(self.index_name)
            status = getattr(desc, "status", None) or desc.get("status", {})
            ready = getattr(status, "ready", None) or status.get("ready", False)
            if ready:
                logger.info("Index ready.")
                return
            time.sleep(1)
        logger.warning("Index creation timeout—check Pinecone console.")

    def get_index(self):
        return self.pc.Index(self.index_name)

    def upsert_vectors(self, vectors: List[Dict], batch_size=100):
        idx = self.get_index()
        total = len(vectors)
        for i in range(0, total, batch_size):
            batch = vectors[i:i + batch_size]
            formatted = [
                {"id": v["id"], "values": v["values"], "metadata": v.get("metadata", {})}
                for v in batch
            ]
            idx.upsert(vectors=formatted)
            logger.info(f"Upserted {i + len(batch)}/{total}")
            time.sleep(0.3)
        logger.info("All vectors uploaded successfully.")

    def search(self, query_vector: List[float], top_k=5, filter_dict: Optional[Dict] = None):
        idx = self.get_index()
        resp = idx.query(vector=query_vector, top_k=top_k, include_metadata=True, filter=filter_dict)
        matches = []
        for m in getattr(resp, "matches", []) or resp.get("matches", []):
            matches.append({
                "id": getattr(m, "id", None) or m.get("id"),
                "score": getattr(m, "score", None) or m.get("score"),
                "metadata": getattr(m, "metadata", None) or m.get("metadata", {}),
            })
        return matches


if __name__ == "__main__":
    vs = VectorService()
    vs.create_index()
    print("✅ Pinecone index is ready:", vs.index_name)

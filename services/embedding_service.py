# services/embedding_service.py
"""
Embedding Service - Google Embeddings Only (Production)
With file-based caching for performance
"""
import os
import sys
import json
import hashlib
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import Config
from utils.logger import logger

try:
    import google.generativeai as genai
except ImportError:
    raise ImportError("Google AI package not installed. Run: pip install google-generativeai")

CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "embeddings.json"


class EmbeddingService:
    """Google Embeddings service with caching"""
    
    def __init__(self):
        """Initialize Google Gemini embeddings"""
        if not Config.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY not found in environment.\n"
                "Please set it in your .env file."
            )
        
        try:
            genai.configure(api_key=Config.GOOGLE_API_KEY)
            self.model = Config.GOOGLE_EMBEDDING_MODEL
            self.dimension = 768  # Google text-embedding-004 dimension
            self.provider = "google"
            
            # Load cache
            self._cache = {}
            self._load_cache()
            
            # Test connection
            #logger.info("Initializing Google Embeddings...")
            test_result = genai.embed_content(
                model=self.model,
                content="test",
                task_type="retrieval_document"
            )
            self.dimension = len(test_result["embedding"])
            
            #logger.info(f"Google Embeddings ready (dim={self.dimension})")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Embeddings: {e}")
            raise RuntimeError(
                f"Google Embeddings initialization failed: {e}\n"
                "Please check your GOOGLE_API_KEY"
            )
    
    def _load_cache(self):
        """Load embedding cache from disk"""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                #logger.info(f"Loaded {len(self._cache)} cached embeddings")
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
            self._cache = {}
    
    def _save_cache(self):
        """Save embedding cache to disk"""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._cache, f)
        except Exception as e:
            logger.warning(f"Could not save cache: {e}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using Google Gemini
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        text = text.strip()
        if not text:
            raise ValueError("Empty text provided for embedding")
        
        # Check cache first
        cache_key = hashlib.sha256(text.encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Generate embedding
            result = genai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_document"
            )
            
            embedding = result["embedding"]
            
            # Cache the result
            self._cache[cache_key] = embedding
            
            # Periodically save cache
            if len(self._cache) % 50 == 0:
                self._save_cache()
            
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise RuntimeError(f"Failed to generate embedding: {e}")
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        total = len(texts)
        
        for i, text in enumerate(texts, 1):
            try:
                emb = self.generate_embedding(text)
                embeddings.append(emb)
                
                if i % 10 == 0:
                    logger.info(f"Embedded {i}/{total} texts")
                    
            except Exception as e:
                logger.error(f"Failed to embed text {i}: {e}")
                raise
        
        # Save cache after batch
        self._save_cache()
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get embedding vector dimension"""
        return self.dimension
    
    def get_provider_info(self) -> dict:
        """Get provider information"""
        return {
            "provider": self.provider,
            "model": self.model,
            "dimension": self.dimension,
            "cache_size": len(self._cache)
        }


# Test
if __name__ == "__main__":
    print("Testing Google Embeddings...\n")
    
    try:
        svc = EmbeddingService()
        info = svc.get_provider_info()
        
        print(f"Provider: {info['provider']}")
        print(f"Model: {info['model']}")
        print(f"Dimension: {info['dimension']}")
        print(f"Cached embeddings: {info['cache_size']}")
        
        # Test embedding
        text = "Beautiful beaches in Vietnam"
        emb = svc.generate_embedding(text)
        
        print(f"\nTest embedding generated: {len(emb)} dimensions")
        print(f"Sample values: {emb[:5]}")
        print("\nSuccess!")
        
    except Exception as e:
        print(f"\nError: {e}")
        import sys
        sys.exit(1)
# test_connections.py
from config import Config
from services.embedding_service import EmbeddingService
from services.vector_service import VectorService
from services.graph_service import GraphService
from services.chat_service import ChatService
from utils.logger import logger

def run_all_tests():
    ok = True
    try:
        Config.validate()
        logger.info("Config validated")
    except Exception as e:
        #logger.error(f"Config validation failed: {e}")
        ok = False

    try:
        emb = EmbeddingService()
        p = emb.generate_embedding("test connection")
        logger.info(f"Embeddings OK (len={len(p)}) - provider: {emb.get_provider_info()}")
    except Exception as e:
        logger.error(f"Embeddings test failed: {e}")
        ok = False

    try:
        vs = VectorService()
        idx = vs.get_index()
        logger.info("Pinecone index access OK")
    except Exception as e:
        logger.error(f"Pinecone test failed: {e}")
        ok = False

    try:
        gs = GraphService()
        nodes = gs.get_all_nodes(limit=3)
        logger.info(f"Neo4j test OK (retrieved {len(nodes)} nodes)")
        gs.close()
    except Exception as e:
        logger.error(f"Neo4j test failed: {e}")
        ok = False

    try:
        cs = ChatService()
        resp = cs.generate_response("Hello", [], None)
        logger.info(f"Chat test OK: {resp[:80]}")
    except Exception as e:
        logger.error(f"Chat test failed: {e}")
        ok = False

    return ok

if __name__ == "__main__":
    import sys
    ok = run_all_tests()
    sys.exit(0 if ok else 1)

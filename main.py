# main.py
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"       # Hide TensorFlow/absl logs
os.environ["GRPC_VERBOSITY"] = "NONE"          # Suppress gRPC logs
os.environ["GRPC_CPP_PLUGIN_LOGGER_LEVEL"] = "ERROR"
os.environ["ABSL_LOG_SEVERITY_THRESHOLD"] = "4"  # Hide absl warnings

from services.embedding_service import EmbeddingService
from services.vector_service import VectorService
from services.graph_service import GraphService
from services.chat_service import ChatService
from config import Config

def print_welcome():
    print("\n--- Vietnam Travel Hybrid Assistant ---")
    print("Type 'exit' to quit.\n")

def main():
    Config.validate()
    emb = EmbeddingService()
    vs = VectorService()
    gs = GraphService()
    cs = ChatService()

    print_welcome()
    while True:
        try:
            q = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not q:
            continue
        if q.lower() in ("exit","quit"):
            print("Bye!")
            break
        q_emb = emb.generate_embedding(q)
        vecs = vs.search(query_vector=q_emb, top_k=Config.TOP_K_RESULTS)
        enriched = gs.enrich_vector_results(vecs)
        ans = cs.generate_response(query=q, context=enriched)
        print("\nAI:", ans, "\n")

if __name__ == "__main__":
    main()

# services/graph_service.py
import os, sys, time
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from typing import List, Dict, Optional
from neo4j import GraphDatabase
from config import Config
from utils.logger import logger

class GraphService:
    def __init__(self):
        if not Config.NEO4J_URI or not Config.NEO4J_PASSWORD:
            raise RuntimeError("Neo4j config missing.")
        self.driver = GraphDatabase.driver(Config.NEO4J_URI, auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD))
        #logger.info("Connected to Neo4j")

    def close(self):
        try:
            self.driver.close()
        except Exception:
            pass

    def get_node_with_relationships(self, node_id: str, max_depth: int = 1) -> Dict:
        q = """
        MATCH (n {id: $node_id})
        OPTIONAL MATCH (n)-[r]-(m)
        RETURN n, collect({rel_type: type(r), node: m}) AS related
        """
        try:
            with self.driver.session() as session:
                result = session.run(q, node_id=node_id)
                rec = result.single()
                if not rec:
                    return {}
                node = dict(rec["n"]) if rec["n"] else {}
                related_raw = rec["related"] or []
                related = []
                for item in related_raw:
                    node_obj = item.get("node") or {}
                    if node_obj:
                        related.append(dict(node_obj))
                return {"node": node, "related_nodes": related}
        except Exception as e:
            logger.error(f"get_node_with_relationships error: {e}")
            return {}

    def enrich_vector_results(self, vector_results: List[Dict]) -> List[Dict]:
        enriched = []
        for vr in vector_results:
            node_id = vr.get("id")
            graph_ctx = {}
            if node_id:
                graph_ctx = self.get_node_with_relationships(node_id)
            enriched.append({**vr, "graph_context": graph_ctx})
        #logger.info(f"Enriched {len(enriched)} vector results with graph data")
        return enriched

    # Debug helpers
    def get_all_nodes(self, limit: int = 100) -> List[Dict]:
        q = "MATCH (n:TravelLocation) RETURN n LIMIT $limit"
        try:
            with self.driver.session() as session:
                res = session.run(q, limit=limit)
                return [dict(r["n"]) for r in res]
        except Exception as e:
            logger.error(f"get_all_nodes error: {e}")
            return []

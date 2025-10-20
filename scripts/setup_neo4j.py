#!/usr/bin/env python3
"""
scripts/setup_neo4j.py
---------------------------------------
Sets up the Neo4j (Aura Cloud or local) database using
the Vietnam travel dataset.

Creates:
• Nodes: City, Attraction, Hotel, Activity, Region, Tag
• Relationships: LOCATED_IN, IN_REGION, CONNECTED_TO, HAS_TAG,
                 SAME_CITY, SIMILAR_TAGS
• Constraints & summary stats
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict
from neo4j import GraphDatabase, basic_auth

# ensure repo root on sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import Config
from utils.logger import logger


DATA_PATH = Path(Config.DATA_FILE or "data/vietnam_travel_dataset.json")


# --------------------------------------------------------------
# Utility: safe print (UTF-8 console compatible)
def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", errors="ignore").decode("utf-8"))


class Neo4jSetup:
    """Handles Neo4j graph creation for Vietnam travel data."""

    def __init__(self):
        uri = getattr(Config, "NEO4J_URI", os.getenv("NEO4J_URI"))
        user = getattr(Config, "NEO4J_USER", os.getenv("NEO4J_USER"))
        password = getattr(Config, "NEO4J_PASSWORD", os.getenv("NEO4J_PASSWORD"))
        if not all([uri, user, password]):
            raise ValueError("Neo4j credentials missing. Set NEO4J_URI/USER/PASSWORD in .env")

        self.driver = GraphDatabase.driver(uri, auth=basic_auth(user, password))
        self._verify_connection()

    def _verify_connection(self):
        with self.driver.session() as s:
            s.run("RETURN 1")
        safe_print(f"Connected to Neo4j at: {Config.NEO4J_URI}")

    def close(self):
        if self.driver:
            self.driver.close()

    # --------------------------------------------------------------
    def clear_database(self):
        with self.driver.session() as s:
            s.run("MATCH (n) DETACH DELETE n")
        safe_print("🧹 Cleared existing database content")

    def create_constraints(self):
        queries = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:City) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Attraction) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (h:Hotel) REQUIRE h.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (ac:Activity) REQUIRE ac.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Region) REQUIRE r.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE",
        ]
        with self.driver.session() as s:
            for q in queries:
                s.run(q)
        safe_print("Database constraints created")

    # --------------------------------------------------------------
    def load_nodes(self, data: List[Dict]):
        """Insert City, Attraction, Hotel, Activity nodes"""
        with self.driver.session() as s:
            for i, item in enumerate(data, 1):
                label = item.get("type", "Other")
                label = label if label in ["City", "Attraction", "Hotel", "Activity"] else "Other"

                props = {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "description": (item.get("description") or "")[:800],
                    "semantic_text": (item.get("semantic_text") or "")[:800],
                    "region": item.get("region"),
                    "city": item.get("city"),
                    "best_time_to_visit": item.get("best_time_to_visit"),
                    "tags": item.get("tags", []),
                    "type": label,
                }

                q = f"MERGE (n:{label} {{id:$id}}) SET n += $props"
                try:
                    s.run(q, id=props["id"], props=props)
                except Exception as e:
                    logger.error(f"Node insert failed ({props['id']}): {e}")

                if i % 100 == 0:
                    safe_print(f"   → Inserted {i}/{len(data)} nodes")

        safe_print("All nodes loaded successfully")

    # --------------------------------------------------------------
    def create_regions(self):
        q = """
        MATCH (c:City)
        WHERE c.region IS NOT NULL AND c.region <> ''
        MERGE (r:Region {name:c.region})
        MERGE (c)-[:IN_REGION]->(r)
        """
        with self.driver.session() as s:
            s.run(q)
        safe_print("Region nodes and IN_REGION links created")

    def create_relationships(self, data: List[Dict]):
        """LOCATED_IN, CONNECTED_TO, HAS_TAG from dataset"""
        with self.driver.session() as s:
            count = 0
            for item in data:
                src = item.get("id")
                if not src:
                    continue

                # LOCATED_IN
                if item.get("city"):
                    q = """
                    MATCH (a {id:$src})
                    OPTIONAL MATCH (c:City)
                    WHERE toLower(c.name)=toLower($city)
                    MERGE (a)-[:LOCATED_IN]->(c)
                    """
                    s.run(q, src=src, city=item["city"])
                    count += 1

                # HAS_TAG
                for tag in item.get("tags", []) or []:
                    q = """
                    MATCH (a {id:$src})
                    MERGE (t:Tag {name:$tag})
                    MERGE (a)-[:HAS_TAG]->(t)
                    """
                    s.run(q, src=src, tag=tag)
                    count += 1

                # connections array
                for conn in item.get("connections", []) or []:
                    rel = (conn.get("relation") or "RELATED_TO").upper().replace(" ", "_")
                    tgt = conn.get("target")
                    if not tgt:
                        continue
                    q = f"""
                    MATCH (a {{id:$src}}), (b {{id:$tgt}})
                    MERGE (a)-[:{rel}]->(b)
                    """
                    s.run(q, src=src, tgt=tgt)
                    count += 1
            safe_print(f"Created {count} base relationships")

    def create_smart_relationships(self):
        """Auto-create SAME_CITY and SIMILAR_TAGS"""
        with self.driver.session() as s:
            s.run("""
                MATCH (a) WHERE a.city IS NOT NULL
                WITH a
                MATCH (b) WHERE b.city IS NOT NULL AND a.city=b.city AND a.id<b.id
                MERGE (a)-[:SAME_CITY]->(b)
            """)
            s.run("""
                MATCH (a) WHERE size(a.tags)>0
                WITH a
                MATCH (b) WHERE size(b.tags)>0 AND a.id<b.id
                WITH a,b,[tag IN a.tags WHERE tag IN b.tags] AS common
                WHERE size(common)>0
                MERGE (a)-[:SIMILAR_TAGS {tags:common}]->(b)
            """)
            s.run("""
                MATCH (c1:City)-[:CONNECTED_TO]->(c2:City)
                MERGE (c2)-[:CONNECTED_TO]->(c1)
            """)
        safe_print(" Smart relationships created (SAME_CITY, SIMILAR_TAGS, CONNECTED_TO symmetry)")

    # --------------------------------------------------------------
    def get_stats(self):
        qn = """
        MATCH (n)
        RETURN
          COUNT(CASE WHEN n:City THEN 1 END) AS cities,
          COUNT(CASE WHEN n:Attraction THEN 1 END) AS attractions,
          COUNT(CASE WHEN n:Hotel THEN 1 END) AS hotels,
          COUNT(CASE WHEN n:Activity THEN 1 END) AS activities,
          COUNT(CASE WHEN n:Region THEN 1 END) AS regions,
          COUNT(CASE WHEN n:Tag THEN 1 END) AS tags
        """
        qr = "MATCH ()-[r]->() RETURN count(r) AS rels"
        with self.driver.session() as s:
            nodes = dict(s.run(qn).single())
            rels = s.run(qr).single()["rels"]
        nodes["relationships"] = rels
        return nodes


# --------------------------------------------------------------
def main():
    safe_print("\n===============================")
    safe_print("   Neo4j Travel Graph Setup")
    safe_print("===============================\n")

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset missing: {DATA_PATH}")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    safe_print(f"📦 Loaded {len(data)} items from dataset")

    neo = Neo4jSetup()
    try:
        neo.clear_database()
        neo.create_constraints()
        neo.load_nodes(data)
        neo.create_regions()
        neo.create_relationships(data)
        neo.create_smart_relationships()
        stats = neo.get_stats()

        safe_print("\nNeo4j setup complete successfully!")
        safe_print("Graph Summary:")
        for k, v in stats.items():
            safe_print(f"   {k.capitalize():15s}: {v}")
        safe_print("")
    finally:
        neo.close()


if __name__ == "__main__":
    main()

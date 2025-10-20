#scripts/visualize_graph.py
import os
from neo4j import GraphDatabase
from pyvis.network import Network
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

NEO_BATCH = 500  # Number of relationships to fetch/visualize

def get_driver():
    """Create and return a Neo4j driver instance"""
    try:
        driver = GraphDatabase.driver(
            Config.NEO4J_URI,
            auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD)
        )
        # Verify connection
        with driver.session() as session:
            session.run("RETURN 1")
        return driver
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        print("Please check your Neo4j connection settings in the .env file or environment variables")
        print("Expected variables:")
        print("- NEO4J_URI (default: bolt://localhost:7687)")
        print("- NEO4J_USER (default: neo4j)")
        print("- NEO4J_PASSWORD (default: password)")
        raise

def fetch_travel_data(tx):
    """Fetch travel-related nodes and relationships"""
    # First get all nodes of interest
    nodes_query = """
    MATCH (n)
    WHERE n:City OR n:Attraction OR n:Hotel OR n:Activity
    RETURN n, labels(n) as labels, id(n) as id
    LIMIT $limit
    """
    nodes_result = tx.run(nodes_query, limit=NEO_BATCH)

    # Then get all relationships between these nodes
    rels_query = """
    MATCH (a)-[r]->(b)
    WHERE (a:City OR a:Attraction OR a:Hotel OR a:Activity)
      AND (b:City OR b:Attraction OR b:Hotel OR b:Activity)
    RETURN a, b, r, id(a) as a_id, id(b) as b_id, type(r) as rel_type
    LIMIT $limit
    """
    rels_result = tx.run(rels_query, limit=NEO_BATCH)

    return {
        'nodes': [dict(record) for record in nodes_result],
        'relationships': [dict(record) for record in rels_result]
    }

def build_travel_pyvis(data, output_html="vietnam_travel_graph.html"):
    """Build and save an interactive travel network visualization"""
    net = Network(
        height="1000px",
        width="100%",
        notebook=False,
        directed=True,
        cdn_resources="remote"
    )

    # Color mapping for different node types
    color_map = {
        'City': '#FF6B6B',      # Coral for cities
        'Attraction': '#4ECDC4', # Teal for attractions
        'Hotel': '#45B7D1',     # Blue for hotels
        'Activity': '#FFA07A'   # Light Salmon for activities
    }

    # Icon mapping for different node types
    icon_map = {
        'City': '🏙️',
        'Attraction': '🗺️',
        'Hotel': '🏨',
        'Activity': '🎭'
    }

    # Add nodes to the network
    nodes = {}
    for node_record in data['nodes']:
        n = node_record['n']
        n_id = node_record['id']
        labels = node_record['labels']
        n_label = labels[0] if labels else 'Unknown'
        n_name = n.get('name', f"Unnamed {n_label}")

        if n_id not in nodes:
            nodes[n_id] = True
            net.add_node(
                n_id,
                label=f"{icon_map.get(n_label, '❓')} {n_name}",
                title=f"ID: {n_id}\nType: {n_label}\nName: {n_name}",
                color=color_map.get(n_label, '#999999'),
                shape='circle',
                size=25 if n_label == 'City' else 20
            )

    # Add relationships to the network
    for rel_record in data['relationships']:
        a_id = rel_record['a_id']
        b_id = rel_record['b_id']
        rel_type = rel_record['rel_type']

        if a_id in nodes and b_id in nodes:
            # Get relationship properties if they exist
            r = rel_record['r']
            edge_title = rel_type
            if hasattr(r, '_properties'):
                for key, value in r._properties.items():
                    edge_title += f"\n{key}: {value}"

            # Different edge colors for different relationship types
            edge_color = {
                'LOCATED_IN': '#FF6347',    # Tomato
                'NEARBY': '#4682B4',        # Steel Blue
                'OFFERS': '#32CD32',        # Lime Green
                'FEATURES': '#DAA520',      # Golden Rod
                'CONNECTED_TO': '#8A2BE2'   # Blue Violet
            }.get(rel_type, '#666666')

            net.add_edge(
                a_id,
                b_id,
                title=edge_title,
                label=rel_type,
                color=edge_color,
                width=1.0,
                arrows='to'
            )

    # Customize physics for better visualization
    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -30000,
          "centralGravity": 0.3,
          "springLength": 200,
          "springConstant": 0.04,
          "damping": 0.09,
          "avoidOverlap": 0.1
        },
        "minVelocity": 0.75,
        "solver": "barnesHut"
      }
    }
    """)

    # Save and show the visualization
    net.show(output_html, notebook=False)
    print(f"✅ Vietnam travel graph visualization saved to {os.path.abspath(output_html)}")
    print(f"Open the file in your browser to view the interactive graph")

def fetch_database_stats(tx):
    """Fetch and print database statistics"""
    # Count nodes by type
    result = tx.run("""
    MATCH (n)
    RETURN
        COUNT(CASE WHEN n:City THEN 1 END) AS cities,
        COUNT(CASE WHEN n:Attraction THEN 1 END) AS attractions,
        COUNT(CASE WHEN n:Hotel THEN 1 END) AS hotels,
        COUNT(CASE WHEN n:Activity THEN 1 END) AS activities,
        COUNT(DISTINCT n:City) AS unique_cities
    """)

    # Count relationships
    rel_result = tx.run("MATCH ()-[r]->() RETURN COUNT(r) AS relationships")
    rel_count = rel_result.single()["relationships"]

    # ✅ Convert Record to dict before modification
    stats = dict(result.single())
    stats["relationships"] = rel_count
    return stats

def main():
    """Main function to execute the visualization"""
    try:
        driver = get_driver()

        with driver.session() as session:
            stats = session.execute_read(fetch_database_stats)
            print("\n=============================================================")
            print("DATABASE STATISTICS")
            print("=============================================================")
            print(f"   Cities:        {stats['cities']}")
            print(f"   Attractions:   {stats['attractions']}")
            print(f"   Hotels:        {stats['hotels']}")
            print(f"   Activities:    {stats['activities']}")
            print(f"   Unique Cities: {stats['unique_cities']}")
            print(f"   Relationships: {stats['relationships']}")
            print("=============================================================")

        with driver.session() as session:
            print("\n🔍 Fetching Vietnam travel data from Neo4j...")
            data = session.execute_read(fetch_travel_data)
            print(f"✅ Fetched {len(data['nodes'])} nodes and {len(data['relationships'])} relationships")

            if not data['nodes']:
                print("⚠️ No travel data found. Make sure you've run setup_neo4j.py first.")
                return

        build_travel_pyvis(data)

    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nPlease make sure:")
        print("1. Neo4j is running")
        print("2. You've run setup_neo4j.py to load the data")
        print("3. Your credentials in .env are correct")
    finally:
        if 'driver' in locals():
            driver.close()
            print("🔌 Neo4j driver closed")

if __name__ == "__main__":
    main()

# 🇻🇳 Vietnam Travel — Hybrid Retrieval Chatbot

### Overview

This project is a **Hybrid Travel Assistant for Vietnam** built using:
- **Pinecone** (Vector Search)
- **Neo4j** (Knowledge Graph)
- **Google Gemma Embeddings** (for semantic search)
- **OpenRouter / OpenAI Chat Models** (for response generation)

It combines **semantic retrieval** with **graph-based enrichment**, allowing the chatbot to generate grounded, itinerary-style travel responses using real relational context (cities, attractions, hotels, activities, and regions).

---

## Project Structure

hybrid_chat_test/
├─ .env # Environment variables (keys, configs)
├─ config.py # Loads .env and constants
├─ requirements.txt
├─ README.md
├─ improvements.md
│
├─ data/
│ └─ vietnam_travel_dataset.json
│
├─ services/
│ ├─ embedding_service.py # Gemma / OpenAI embeddings
│ ├─ vector_service.py # Pinecone vector indexing
│ ├─ graph_service.py # Neo4j graph operations
│ ├─ chat_service.py # Chat model interface (OpenRouter/OpenAI)
│
├─ scripts/
│ ├─ setup_pinecone.py # Builds & uploads embeddings to Pinecone
│ ├─ setup_neo4j.py # Creates nodes/relationships in Neo4j
│ └─ visualize_graph.py # Visualize relationships via PyVis
│
├─ main.py # Interactive chat combining all layers
├─ test_connections.py # Quick sanity tests
└─ .github/workflows/ci.yml # Optional: lint & test pipeline


---

## Setup Instructions (Windows / PowerShell)

### Create Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\activate
Install Dependencies
powershell

Copy code
pip install --upgrade pip
pip install -r requirements.txt
Add Environment Variables
Create a .env file in the root directory:

ini
Copy code
# Neo4j Database (AuraDB or Local)
NEO4J_URI=neo4j+s://<your-neo4j-endpoint>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>

# Pinecone Configuration
PINECONE_API_KEY=pcsk_...
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=vietnam-travel-index
PINECONE_BATCH_SIZE=100

# Embedding & Chat Providers
GOOGLE_API_KEY=<your-gemini-or-gemma-key>
OPENROUTER_API_KEY=<optional-openrouter-key>
OPENAI_API_KEY=<optional-openai-key>

# Defaults
USE_MOCK_EMBEDDINGS=false
USE_MOCK_CHAT=false
DATA_FILE=data/vietnam_travel_dataset.json
Running Each Component
Setup Neo4j Graph
powershell
Copy code
python -m scripts.setup_neo4j
This script:

Loads all cities, attractions, hotels, and activities as nodes.

Creates constraints (id unique per type).

Builds region, tag, and same-city relationships.

Links related nodes based on “connections” from the dataset.

Setup Pinecone Vector Index
powershell
Copy code
python -m scripts.setup_pinecone
This script:

Loads your dataset.

Generates embeddings using Google Gemma (768D).

Creates and populates your Pinecone index.

Optionally runs a quick test query.

Run the Chat Assistant
powershell
Copy code
python main.py
Then type:
create a romantic 4 day itinerary for Vietnam
The assistant:

Embeds your query using Gemma.

Retrieves top semantic matches from Pinecone.

Enriches them with connected nodes from Neo4j.

Builds a detailed, grounded response via OpenRouter / OpenAI.

Visualization (optional)
powershell
Copy code
python -m scripts.visualize_graph
Generates an interactive HTML (neo4j_viz.html) of your graph.

Technology Stack
Layer	Technology	Purpose
Embeddings	Google Gemma (768D)	Free, open-source, robust text embeddings
Vector Store	Pinecone (Serverless)	Fast semantic search across attractions
Graph Store	Neo4j AuraDB	Structured relationships (cities, hotels, activities)
Chat Model	OpenRouter / OpenAI GPT	Generates itinerary & travel explanations
Language	Python 3.10+	Cross-platform scripts & services

Testing
powershell
Copy code
python test_connections.py
Verifies:

Embeddings API

Pinecone index connection

Neo4j driver connection

Chat provider key validity

Notes for Evaluators
Embedding choice: Initially used text-embedding-3-small (1536D) from OpenAI. Later switched to Gemma Embeddings (768D) — open, robust, and free.

Graph modeling: Added smart relations like SAME_CITY, SIMILAR_TAGS, IN_REGION, and HAS_TAG.

Vector enrichment: Each item in Pinecone includes detailed metadata (type, city, tags, etc.).

Prompt engineering: System prompts fuse semantic results and graph facts for coherent, context-grounded answers.

Resilient design: Includes mock embeddings and offline chat fallback for demonstration without API costs.

Troubleshooting
Issue	Cause	Fix
ModuleNotFoundError: config	Script run from wrong folder	Run via python -m scripts.setup_pinecone
VectorService fallback-mock	Pinecone client missing	pip install pinecone-client==3.1.0
Neo4j connection refused	Wrong URI / Neo4j not running	Use Aura URI or start local instance
Chat generation failed: Connection error	Missing or invalid chat API key	Add valid OPENROUTER_API_KEY or OPENAI_API_KEY
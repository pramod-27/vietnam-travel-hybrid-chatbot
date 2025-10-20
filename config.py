# config.py
"""
Configuration management for Vietnam Travel Hybrid Chatbot
Loads settings from .env file
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """Application configuration"""
    
    # ============ Provider Toggles ============
    USE_GOOGLE_EMBEDDINGS = os.getenv("USE_GOOGLE_EMBEDDINGS", "false").lower() == "true"
    USE_OPENROUTER = os.getenv("USE_OPENROUTER", "true").lower() == "true"  # Default to true
    
    # ============ API Keys ============
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # ============ OpenRouter Settings ============
    OPENROUTER_BASE_URL = os.getenv(
        "OPENROUTER_BASE_URL", 
        "https://openrouter.ai/api/v1"
    )
    OPENROUTER_CHAT_MODEL = os.getenv(
        "OPENROUTER_CHAT_MODEL",
        "meta-llama/llama-3.1-8b-instruct:free"  # Free model as default
    )
    
    # ============ Embedding Models ============
    EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    GOOGLE_EMBEDDING_MODEL = os.getenv(
        "GOOGLE_EMBEDDING_MODEL", 
        "models/text-embedding-004"
    )
    
    # ============ Chat Models ============
    CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    
    # ============ Pinecone Configuration ============
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "vietnam-travel-index")
    
    # ============ Vector Dimension ============
    # Auto-adjust based on embedding provider
    if USE_GOOGLE_EMBEDDINGS:
        VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "768"))  # Google default
    else:
        VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "1536"))  # OpenAI default
    
    # ============ Neo4j Configuration ============
    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
    
    # ============ Application Settings ============
    TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))
    DATA_FILE = os.getenv("DATA_FILE", "data/vietnam_travel_dataset.json")
    LOG_FILE = os.getenv("LOG_FILE", "logs/chatbot.log")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        missing = []
        warnings = []
        
        # Check chat providers
        if not any([cls.OPENAI_API_KEY, cls.OPENROUTER_API_KEY, cls.GOOGLE_API_KEY]):
            warnings.append("No chat provider key found (OPENAI/OPENROUTER/GOOGLE)")
        
        # Check embedding providers
        if not any([cls.OPENAI_API_KEY, cls.GOOGLE_API_KEY]):
            warnings.append("No embedding provider key found")
        
        # Critical services
        if not cls.PINECONE_API_KEY:
            missing.append("PINECONE_API_KEY")
        
        if not cls.NEO4J_URI:
            missing.append("NEO4J_URI")
        
        if not cls.NEO4J_PASSWORD:
            missing.append("NEO4J_PASSWORD")
        
        # Report issues
        if missing:
            raise ValueError(
                f"❌ Missing required configuration: {', '.join(missing)}\n"
                "Please check your .env file."
            )
        
        if warnings:
            print("⚠️  Configuration warnings:")
            for w in warnings:
                print(f"   - {w}")
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration (for debugging)"""
        print("\n" + "="*60)
        print("CONFIGURATION")
        print("="*60)
        
        print("\n🔑 API Keys:")
        print(f"   OpenAI:      {'✅ Set' if cls.OPENAI_API_KEY else '❌ Not set'}")
        print(f"   OpenRouter:  {'✅ Set' if cls.OPENROUTER_API_KEY else '❌ Not set'}")
        print(f"   Google:      {'✅ Set' if cls.GOOGLE_API_KEY else '❌ Not set'}")
        
        print("\n🧠 Providers:")
        print(f"   Use OpenRouter: {cls.USE_OPENROUTER}")
        print(f"   Use Google:     {cls.USE_GOOGLE_EMBEDDINGS}")
        
        print("\n🤖 Models:")
        print(f"   Chat:       {cls.OPENROUTER_CHAT_MODEL if cls.USE_OPENROUTER else cls.CHAT_MODEL}")
        print(f"   Embedding:  {cls.GOOGLE_EMBEDDING_MODEL if cls.USE_GOOGLE_EMBEDDINGS else cls.EMBEDDING_MODEL}")
        
        print("\n📊 Services:")
        print(f"   Pinecone:   {'✅ Configured' if cls.PINECONE_API_KEY else '❌ Not configured'}")
        print(f"   Neo4j:      {'✅ Configured' if cls.NEO4J_URI else '❌ Not configured'}")
        
        print("="*60 + "\n")


# Validate on import
try:
    Config.validate()
except ValueError as e:
    print(f"\n{e}\n")
    import sys
    sys.exit(1)
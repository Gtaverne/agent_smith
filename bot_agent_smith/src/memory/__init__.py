import os
from typing import Literal, Union, Dict, Any, Type

from src.core.logger import logger
from .interfaces import VectorDBClient, MessageRepository, UserRepository

def get_vector_db_config() -> Dict[str, Any]:
    """
    Get vector database configuration from environment variables
    
    Returns:
        Dict containing vector database configuration
    """
    config = {
        "type": os.getenv("VECTOR_DB_TYPE", "chroma").lower(),
        
        # Chroma configuration
        "chroma": {
            "host": os.getenv("CHROMA_HOST", "localhost"),
            "port": int(os.getenv("CHROMA_PORT", "8184")),
        },
        
        # GCP Vector Search configuration
        "gcp_vector_search": {
            "project_id": os.getenv("GCP_PROJECT_ID", ""),
            "location": os.getenv("GCP_LOCATION", "us-central1"),
            "index_endpoint_name": os.getenv("GCP_INDEX_ENDPOINT", "agent-smith-vector-endpoint"),
            "messages_index_id": os.getenv("GCP_MESSAGES_INDEX", "messages-index"),
            "users_index_id": os.getenv("GCP_USERS_INDEX", "users-index"),
            "dimensions": int(os.getenv("EMBEDDING_DIMENSION", "384")),
        },

        # Qdrant configuration
        "qdrant": {
            "url": os.getenv("QDRANT_URL", ""),
            "api_key": os.getenv("QDRANT_API_KEY", ""),
            "collection_prefix": os.getenv("QDRANT_COLLECTION_PREFIX", "agent_smith_"),
            "dimensions": int(os.getenv("EMBEDDING_DIMENSION", "384")),
        }
    }
    
    return config

def create_vector_db_client(
    db_type: Literal["chroma", "gcp_vector_search", "qdrant"] = None,
    **kwargs
) -> VectorDBClient:
    """
    Create vector database client based on configuration
    
    Args:
        db_type: Type of vector database (chroma or gcp_vector_search)
        **kwargs: Override configuration parameters
        
    Returns:
        Vector database client
    """
    # Get configuration
    config = get_vector_db_config()
    
    # Override with kwargs
    if db_type:
        config["type"] = db_type
    
    # Create client based on type
    if config["type"] == "chroma":
        # Import here to avoid circular imports and keep concerns separated
        from src.memory.chroma_db.chroma import ChromaClient
        
        # Override Chroma config with kwargs
        chroma_config = config["chroma"]
        chroma_config.update(kwargs)
        
        logger.info(f"Creating ChromaDB client at {chroma_config['host']}:{chroma_config['port']}")
        return ChromaClient(
            host=chroma_config["host"],
            port=chroma_config["port"]
        )
        
    elif config["type"] == "gcp_vector_search":
        # Override GCP config with kwargs
        gcp_config = config["gcp_vector_search"]
        gcp_config.update(kwargs)
        
        # Validate required params
        if not gcp_config["project_id"]:
            raise ValueError("GCP_PROJECT_ID environment variable is required for GCP Vector Search")
        
        # Import GCP vector search implementation only when needed
        from src.memory.gcp_vector_search.gcp_vector_search import GCPVectorSearchClient
        
        logger.info(f"Creating GCP Vector Search client for project {gcp_config['project_id']}")
        return GCPVectorSearchClient(**gcp_config)
    
    elif config["type"] == "qdrant":
        # Override Qdrant config with kwargs
        qdrant_config = config["qdrant"]
        qdrant_config.update(kwargs)
        
        # Validate required params
        if not qdrant_config["url"]:
            raise ValueError("QDRANT_URL environment variable is required for Qdrant")
        
        # Import Qdrant implementation only when needed
        from src.memory.qdrant.qdrant import QdrantClient
        
        logger.info(f"Creating Qdrant client with URL: {qdrant_config['url']}")
        return QdrantClient(**qdrant_config)
        
    else:
        raise ValueError(f"Unsupported vector database type: {config['type']}")

def create_message_repository(vector_db_client) -> MessageRepository:
    """
    Create message repository based on client type
    
    Args:
        vector_db_client: Vector database client
        
    Returns:
        Message repository
    """
    # Determine the type of client and create the corresponding repository
    client_module = vector_db_client.__class__.__module__
    
    if "chroma_db.chroma" in client_module:
        from src.memory.chroma_db.chroma import MessageRepository as ChromaMessageRepository
        return ChromaMessageRepository(vector_db_client)
    
    elif "gcp_vector_search" in client_module:
        from src.memory.gcp_vector_search.gcp_vector_search import MessageRepository as GCPMessageRepository
        return GCPMessageRepository(vector_db_client)
    
    elif "qdrant.qdrant" in client_module:
        from src.memory.qdrant.qdrant import MessageRepository as QdrantMessageRepository
        return QdrantMessageRepository(vector_db_client)
    
    else:
        raise ValueError(f"Unsupported vector database client: {type(vector_db_client)}")

def create_user_repository(vector_db_client) -> UserRepository:
    """
    Create user repository based on client type
    
    Args:
        vector_db_client: Vector database client
        
    Returns:
        User repository
    """
    # Determine the type of client and create the corresponding repository
    client_module = vector_db_client.__class__.__module__
    
    if "chroma_db.chroma" in client_module:
        from src.memory.chroma_db.chroma import UserRepository as ChromaUserRepository
        return ChromaUserRepository(vector_db_client)
    
    elif "gcp_vector_search" in client_module:
        from src.memory.gcp_vector_search.gcp_vector_search import UserRepository as GCPUserRepository
        return GCPUserRepository(vector_db_client)
    
    elif "qdrant.qdrant" in client_module:
        from src.memory.qdrant.qdrant import UserRepository as QdrantUserRepository
        return QdrantUserRepository(vector_db_client)
    
    else:
        raise ValueError(f"Unsupported vector database client: {type(vector_db_client)}")
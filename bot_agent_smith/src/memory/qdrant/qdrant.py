from typing import List, Dict, Any, Optional, Union
from datetime import datetime, UTC
import os
import json

from qdrant_client import QdrantClient as QClient
from qdrant_client.http import models
from qdrant_client.http.models import VectorParams, Distance, PointStruct, SearchRequest

from src.core.types import Message, Conversation, UserProfile, Author
from src.core.logger import logger
from src.memory.interfaces import VectorDBClient, MessageRepository as MessageRepositoryInterface, UserRepository as UserRepositoryInterface

class QdrantClient(VectorDBClient):
    """Client for Qdrant vector database with cloud and self-hosted support"""
    
    def __init__(
        self, 
        url: str = None,
        api_key: str = None,
        dimensions: int = None,  # Make this optional
        collection_prefix: str = "agent_smith_",
        embedding_model_name: str = "all-MiniLM-L6-v2"  # Add model name
    ):
        """
        Initialize the Qdrant Client
        
        Args:
            url: Qdrant server URL (e.g., https://your-cluster-url.qdrant.io)
            api_key: Qdrant API key for authentication
            dimensions: Dimension of embeddings to be stored
            collection_prefix: Prefix for collection names to avoid conflicts
        """
        # Determine embedding dimension based on model
        if dimensions is None:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(embedding_model_name)
            self.dimensions = model.get_sentence_embedding_dimension()
            logger.info(f"Using embedding dimension {self.dimensions} from model {embedding_model_name}")
        else:
            self.dimensions = dimensions
        
        self.collection_prefix = collection_prefix        

        # Initialize Qdrant client
        self.client = QClient(
            url=url,
            api_key=api_key,
        )
        
        # Collection names with prefix
        self.messages_collection_name = f"{collection_prefix}messages"
        self.users_collection_name = f"{collection_prefix}users"
        self.conversations_collection_name = f"{collection_prefix}conversations"
        
        # Initialize collections
        self._init_collections()
        
        # Create index handles for repository access
        self.messages = MessageIndexHandle(
            client=self.client,
            collection_name=self.messages_collection_name,
            dimensions=self.dimensions
        )
        
        self.users = UserIndexHandle(
            client=self.client,
            collection_name=self.users_collection_name,
            dimensions=self.dimensions
        )
        
        self.conversations = ConversationIndexHandle(
            client=self.client,
            collection_name=self.conversations_collection_name
        )
        
        logger.info(f"Initialized Qdrant client with URL: {url}")
    
    def _init_collections(self):
        """Initialize Qdrant collections for messages, users, and conversations"""
        # Initialize messages collection
        self._create_collection_if_not_exists(
            collection_name=self.messages_collection_name,
            has_vectors=True
        )
        
        # Initialize users collection
        self._create_collection_if_not_exists(
            collection_name=self.users_collection_name,
            has_vectors=True
        )
        
        # Initialize conversations collection (no vectors, just metadata)
        self._create_collection_if_not_exists(
            collection_name=self.conversations_collection_name,
            has_vectors=False
        )
    
    def _create_collection_if_not_exists(self, collection_name: str, has_vectors: bool = True):
        """Create a collection if it doesn't exist"""
        # Check if collection exists
        collections = self.client.get_collections().collections
        collection_exists = any(c.name == collection_name for c in collections)
        
        # Delete collection if it exists
        if collection_exists:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted existing collection {collection_name}")
        
        # Create collection with correct dimensions
        vector_params = None
        if has_vectors:
            vector_params = VectorParams(
                size=self.dimensions,
                distance=Distance.COSINE
            )
        
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=vector_params
        )
        logger.info(f"Created collection {collection_name} with dimension {self.dimensions}")
    
    def get_messages(self, **kwargs) -> Dict[str, Any]:
        """Get messages data"""
        return self.messages.get(**kwargs)
    
    def get_users(self, **kwargs) -> Dict[str, Any]:
        """Get users data"""
        return self.users.get(**kwargs)
    
    def get_conversations(self, **kwargs) -> Dict[str, Any]:
        """Get conversations data"""
        return self.conversations.get(**kwargs)
    
    def reset_collections(self):
        """Reset all collections - use with caution!"""
        logger.warning("Resetting all Qdrant collections!")
        
        try:
            # Delete existing collections
            for collection_name in [self.messages_collection_name, self.users_collection_name, self.conversations_collection_name]:
                try:
                    self.client.delete_collection(collection_name=collection_name)
                    logger.info(f"Deleted collection {collection_name}")
                except Exception as e:
                    logger.warning(f"Error deleting collection {collection_name}: {e}")
                    
            # Reinitialize collections
            self._init_collections()
            logger.info("Collections reset complete")
        except Exception as e:
            logger.error(f"Error resetting collections: {e}")
            raise


class MessageIndexHandle:
    """Handle for the messages collection"""
    
    def __init__(self, client, collection_name: str, dimensions: int):
        self.client = client
        self.collection_name = collection_name
        self.dimensions = dimensions
    
    def add(self, message: Message):
        """Add a message to the Qdrant collection"""
        # Convert message to a dictionary
        message_dict = message.to_dict()
        
        # If no vector, we'll use a placeholder with all zeros
        vector = message.embedding if message.embedding else [0.0] * self.dimensions
        if not message.embedding:
            logger.warning(f"No embedding for message {message.id}, using zero vector")
        
        # Create Qdrant point
        point = PointStruct(
            id=message.id,
            payload=message_dict,
            vector=vector  # Now vector is always defined
        )
        
        # Upsert point to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        logger.info(f"Added message {message.id} to Qdrant")
    
    def get(self, message_id: str = None) -> Union[Optional[Message], Dict[str, Any]]:
        """Get a message by ID or get all messages"""
        if message_id:
            # Retrieve single message
            try:
                point = self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=[message_id]
                )
                
                if not point:
                    return None
                
                # Convert to Message
                return Message.from_dict(point[0].payload)
            except Exception as e:
                logger.error(f"Error retrieving message {message_id}: {e}")
                return None
        else:
            # For compatibility with Chroma API - return all IDs and metadatas
            # Note: This should be used carefully with pagination for large collections
            points = self.client.scroll(
                collection_name=self.collection_name,
                limit=100  # Adjust this limit as needed
            )[0]
            
            data = {
                "ids": [],
                "metadatas": []
            }
            
            for point in points:
                data["ids"].append(point.id)
                data["metadatas"].append(point.payload)
            
            return data
    
    def get_by_conversation(self, conversation_id: str) -> List[Message]:
        """Get all messages in a conversation"""
        # Scroll through points with filter
        points = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="conversation_id",
                        match=models.MatchValue(value=conversation_id)
                    )
                ]
            ),
            limit=1000  # Adjust this limit as needed
        )[0]
        
        # Convert to Messages
        return [Message.from_dict(point.payload) for point in points]
    
    def search(self, query: str, n_results: int = 10) -> List[Message]:
        """
        Search for messages similar to the query
        
        Note: This is a simplified implementation that uses text search
        for demonstration. In a real implementation, you would generate
        an embedding for the query and use vector search.
        """
        # First try with text match
        points = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="content",
                        match=models.MatchText(text=query)
                    )
                ]
            ),
            limit=n_results
        )[0]
        
        # If no results, try a more lenient search
        if not points:
            logger.info("No exact matches, trying partial matching")
            
            # Split the query into words for more matches
            query_words = query.lower().split()
            
            # Use any word matching
            should_conditions = []
            for word in query_words:
                if len(word) > 3:  # Only use significant words
                    should_conditions.append(
                        models.FieldCondition(
                            key="content",
                            match=models.MatchText(text=word)
                        )
                    )
            
            if should_conditions:
                points = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=models.Filter(
                        should=should_conditions,
                        min_should=1  # At least one condition must match
                    ),
                    limit=n_results
                )[0]
        
        # Convert to Messages
        return [Message.from_dict(point.payload) for point in points]


class UserIndexHandle:
    """Handle for the users collection"""
    
    def __init__(self, client, collection_name: str, dimensions: int):
        self.client = client
        self.collection_name = collection_name
        self.dimensions = dimensions
    
    def add(self, user: UserProfile):
        """Add a user to the Qdrant collection"""
        # Convert user to a dictionary
        user_dict = user.to_dict()
        
        # If no vector, we'll use a placeholder with all zeros
        vector = user.embedding if user.embedding else [0.0] * self.dimensions
        if not user.embedding:
            logger.warning(f"No embedding for user {user.id}, using zero vector")
        
        # Create Qdrant point
        point = PointStruct(
            id=user.id,
            payload=user_dict,
            vector=vector  # Now vector is always defined
        )
        
        # Upsert point to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        logger.info(f"Added user {user.id} to Qdrant")
    
    def get(self, user_id: str = None) -> Union[Optional[UserProfile], Dict[str, Any]]:
        """Get a user by ID or get all users"""
        if user_id:
            # Retrieve single user
            try:
                point = self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=[user_id]
                )
                
                if not point:
                    return None
                
                # Convert to UserProfile
                return UserProfile.from_dict(point[0].payload)
            except Exception as e:
                logger.error(f"Error retrieving user {user_id}: {e}")
                return None
        else:
            # For compatibility with Chroma API - return all IDs and metadatas
            points = self.client.scroll(
                collection_name=self.collection_name,
                limit=100  # Adjust this limit as needed
            )[0]
            
            data = {
                "ids": [],
                "metadatas": []
            }
            
            for point in points:
                data["ids"].append(point.id)
                data["metadatas"].append(point.payload)
            
            return data
    
    def get_by_discord_id(self, discord_id: str) -> Optional[UserProfile]:
        """Get a user by Discord ID"""
        # Search for user with matching discord_id in payload field, not as ID
        points = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="discord_id",
                        match=models.MatchValue(value=discord_id)
                    )
                ]
            ),
            limit=1
        )[0]
        
        if not points:
            return None
        
        # Convert to UserProfile
        return UserProfile.from_dict(points[0].payload)
    
    def update(self, user: UserProfile):
        """Update a user in the Qdrant collection"""
        # Same as add since upsert will overwrite existing user
        self.add(user)


class ConversationIndexHandle:
    """Handle for the conversations collection"""
    
    def __init__(self, client, collection_name: str):
        self.client = client
        self.collection_name = collection_name
    
    def add(self, conversation: Conversation):
        """Add a conversation to the Qdrant collection"""
        # Convert conversation to a dictionary
        conversation_dict = conversation.to_dict()
        
        # Create Qdrant point
        point = PointStruct(
            id=conversation.id,
            payload=conversation_dict,
            vector=None  # Conversations don't need vectors
        )
        
        # Upsert point to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        logger.info(f"Added conversation {conversation.id} to Qdrant")
    
    def get(self, conversation_id: str = None) -> Union[Optional[Conversation], Dict[str, Any]]:
        """Get a conversation by ID or get all conversations"""
        if conversation_id:
            # Retrieve single conversation
            try:
                point = self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=[conversation_id]
                )
                
                if not point:
                    return None
                
                # Convert to Conversation
                return Conversation.from_dict(point[0].payload)
            except Exception as e:
                logger.error(f"Error retrieving conversation {conversation_id}: {e}")
                return None
        else:
            # For compatibility with Chroma API - return all IDs and metadatas
            points = self.client.scroll(
                collection_name=self.collection_name,
                limit=100  # Adjust this limit as needed
            )[0]
            
            data = {
                "ids": [],
                "metadatas": []
            }
            
            for point in points:
                data["ids"].append(point.id)
                data["metadatas"].append(point.payload)
            
            return data


class MessageRepository(MessageRepositoryInterface):
    """Repository for message operations using Qdrant"""
    
    def __init__(self, client: QdrantClient):
        self.client = client
        self.collection = client.messages
    
    def add(self, message: Message) -> None:
        """Add a message to the repository"""
        self.collection.add(message)
    
    def get(self, message_id: str) -> Optional[Message]:
        """Get a message by ID"""
        return self.collection.get(message_id)
    
    def get_by_conversation(self, conversation_id: str) -> List[Message]:
        """Get all messages in a conversation"""
        return self.collection.get_by_conversation(conversation_id)
    
    def search(self, query: str, n_results: int = 10) -> List[Message]:
        """Search for messages similar to the query"""
        return self.collection.search(query, n_results)


class UserRepository(UserRepositoryInterface):
    """Repository for user operations using Qdrant"""
    
    def __init__(self, client: QdrantClient):
        self.client = client
        self.collection = client.users
    
    def add(self, user: UserProfile) -> None:
        """Add a user to the repository"""
        self.collection.add(user)
    
    def get(self, user_id: str) -> Optional[UserProfile]:
        """Get a user by ID"""
        return self.collection.get(user_id)
    
    def get_by_discord_id(self, discord_id: str) -> Optional[UserProfile]:
        """Get a user by Discord ID"""
        return self.collection.get_by_discord_id(discord_id)
    
    def update(self, user: UserProfile) -> None:
        """Update a user in the repository"""
        self.collection.update(user)
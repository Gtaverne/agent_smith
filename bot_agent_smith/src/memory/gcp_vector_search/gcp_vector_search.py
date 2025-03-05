from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta, UTC
import uuid
import os
import json
import re

from google.cloud import aiplatform
from google.cloud import firestore
from google.api_core.exceptions import NotFound

from src.core.types import Message, Conversation, UserProfile, Author
from src.core.logger import logger
from src.memory.interfaces import VectorDBClient, MessageRepository as MessageRepositoryInterface, UserRepository as UserRepositoryInterface

class GCPVectorSearchClient(VectorDBClient):
    """Client for Google Vertex AI Vector Search with Firestore metadata storage"""
    
    def __init__(
        self, 
        project_id: str,
        location: str = "us-central1",
        index_endpoint_name: str = "agent-smith-vector-endpoint",
        messages_index_id: str = "messages-index",
        users_index_id: str = "users-index",
        dimensions: int = 384,  # Default embedding dimension
    ):
        """
        Initialize the GCP Vector Search client
        
        Args:
            project_id: Google Cloud project ID
            location: Google Cloud region
            index_endpoint_name: Name of the Vector Search index endpoint
            messages_index_id: ID of the messages index
            users_index_id: ID of the users index
            dimensions: Dimension of the embeddings
        """
        self.project_id = project_id
        self.location = location
        self.dimensions = dimensions
        
        # Initialize Vertex AI client
        aiplatform.init(project=project_id, location=location)
        
        # Initialize Firestore client
        self.firestore_client = firestore.Client(project=project_id)
        
        # Set up references to Firestore collections
        self.messages_collection = self.firestore_client.collection("messages")
        self.conversations_collection = self.firestore_client.collection("conversations")
        self.users_collection = self.firestore_client.collection("users")
        
        # Set up Vector Search indexes and endpoints
        self.index_endpoint_name = index_endpoint_name
        self.messages_index_id = messages_index_id
        self.users_index_id = users_index_id
        
        # Initialize or get Vector Search endpoint and indexes
        self._init_vector_search()
        
        # Create index handles for convenient access
        self.messages = MessageIndexHandle(
            self.messages_collection,
            self.index_endpoint,
            self.messages_index,
            self.dimensions,
            self.firestore_client
        )
        
        self.conversations = ConversationIndexHandle(
            self.conversations_collection,
            self.firestore_client
        )
        
        self.users = UserIndexHandle(
            self.users_collection,
            self.index_endpoint,
            self.users_index,
            self.dimensions,
            self.firestore_client
        )
        
        logger.info(f"Initialized GCP Vector Search client for project {project_id}")
    
    def _init_vector_search(self):
        """Initialize or get Vector Search endpoint and indexes"""
        # Get or create index endpoint
        endpoint_exists = False
        index_endpoints = aiplatform.MatchingEngineIndexEndpoint.list()
        
        for endpoint in index_endpoints:
            if endpoint.display_name == self.index_endpoint_name:
                self.index_endpoint = endpoint
                endpoint_exists = True
                logger.info(f"Found existing index endpoint: {self.index_endpoint_name}")
                break
                
        if not endpoint_exists:
            logger.info(f"Creating new index endpoint: {self.index_endpoint_name}")
            self.index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
                display_name=self.index_endpoint_name,
                public_endpoint_enabled=True  # Enable public endpoint
            )
        
        # Get or create message index
        messages_index_exists = False
        users_index_exists = False
        
        indexes = aiplatform.MatchingEngineIndex.list()
        for index in indexes:
            if index.display_name == self.messages_index_id:
                self.messages_index = index
                messages_index_exists = True
                logger.info(f"Found existing messages index: {self.messages_index_id}")
            elif index.display_name == self.users_index_id:
                self.users_index = index
                users_index_exists = True
                logger.info(f"Found existing users index: {self.users_index_id}")
                
        if not messages_index_exists:
            logger.info(f"Creating new messages index: {self.messages_index_id}")
            self.messages_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
                display_name=self.messages_index_id,
                dimensions=self.dimensions,
                description="Message embeddings index",
                approximate_neighbors_count=150,
                distance_measure_type="DOT_PRODUCT_DISTANCE"
            )
        
        if not users_index_exists:
            logger.info(f"Creating new users index: {self.users_index_id}")
            self.users_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
                display_name=self.users_index_id,
                dimensions=self.dimensions,
                description="User embeddings index",
                approximate_neighbors_count=150,
                distance_measure_type="DOT_PRODUCT_DISTANCE"
            )
            
        # Deploy indexes to endpoint if needed
        self._deploy_indexes()
    
    def _deploy_indexes(self):
        """Deploy indexes to the endpoint if not already deployed"""
        # Get list of deployed indexes
        deployed_indexes = [index.index for index in self.index_endpoint.deployed_indexes]
        
        # Deploy messages index if not already deployed
        if self.messages_index.name not in deployed_indexes:
            logger.info(f"Deploying messages index to endpoint")
            self.index_endpoint.deploy_index(
                index=self.messages_index,
                deployed_index_id=self.messages_index_id
            )
        
        # Deploy users index if not already deployed
        if self.users_index.name not in deployed_indexes:
            logger.info(f"Deploying users index to endpoint")
            self.index_endpoint.deploy_index(
                index=self.users_index,
                deployed_index_id=self.users_index_id
            )
    
    def get_messages(self, **kwargs) -> Dict[str, Any]:
        """Get messages collection data"""
        return self.messages.get(**kwargs)
    
    def get_users(self, **kwargs) -> Dict[str, Any]:
        """Get users collection data"""
        return self.users.get(**kwargs)
    
    def get_conversations(self, **kwargs) -> Dict[str, Any]:
        """Get conversations collection data"""
        return self.conversations.get(**kwargs)


class MessageIndexHandle:
    """Handle for the messages index and collection"""
    
    def __init__(
        self, 
        collection, 
        index_endpoint, 
        index,
        dimensions: int,
        firestore_client
    ):
        self.collection = collection
        self.index_endpoint = index_endpoint
        self.index = index
        self.dimensions = dimensions
        self.firestore_client = firestore_client
    
    def add(self, message: Message):
        """Add a message to the index and Firestore"""
        # Convert message to a dictionary
        message_dict = message.to_dict()
        
        # Store in Firestore
        self.collection.document(message.id).set(message_dict)
        
        # Add to vector index if embedding exists
        if message.embedding:
            self.index.upsert_embeddings(
                embeddings=[message.embedding],
                ids=[message.id],
                metadata_list=[{
                    "id": message.id,
                    "conversation_id": message.conversation_id,
                    "type": message.type.value,
                    "author_id": message.author.id
                }]
            )
        else:
            logger.warning(f"No embedding for message {message.id}, skipping vector index")
    
    def get(self, message_id: str) -> Optional[Message]:
        """Get a message by ID"""
        # Get from Firestore
        doc_ref = self.collection.document(message_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
            
        return Message.from_dict(doc.to_dict())
    
    def get_by_conversation(self, conversation_id: str) -> List[Message]:
        """Get all messages in a conversation"""
        # Query Firestore
        query = self.collection.where("conversation_id", "==", conversation_id)
        docs = query.stream()
        
        return [Message.from_dict(doc.to_dict()) for doc in docs]
    
    def search(self, query: str, n_results: int = 10) -> List[Message]:
        """
        Search for messages similar to the query
        
        Note: This is a simplified implementation that assumes embeddings
        are generated elsewhere before adding to the index.
        """
        # For this example, we'll use a simple keyword search in Firestore
        # In a real implementation, you would:
        # 1. Generate an embedding for the query
        # 2. Search the vector index using the embedding
        # 3. Return the matched documents
        
        logger.warning("Vector search not fully implemented - using keyword fallback")
        
        # Simple keyword search fallback
        query_words = query.lower().split()
        results = []
        
        # Query all messages (inefficient for production)
        all_docs = self.collection.stream()
        
        for doc in all_docs:
            data = doc.to_dict()
            content = data.get("content", "").lower()
            
            # Simple relevance score based on word matches
            score = sum(1 for word in query_words if word in content)
            
            if score > 0:
                results.append((score, Message.from_dict(data)))
        
        # Sort by relevance and limit to n_results
        results.sort(reverse=True, key=lambda x: x[0])
        return [msg for _, msg in results[:n_results]]
    
    def delete(self, ids: List[str] = None):
        """Delete messages by ID"""
        if not ids:
            return
            
        # Delete from Firestore
        batch = self.firestore_client.batch()
        for id in ids:
            batch.delete(self.collection.document(id))
        batch.commit()
        
        # Delete from vector index
        self.index.remove_embeddings(ids=ids)


class MessageRepository(MessageRepositoryInterface):
    """Repository for message operations"""
    
    def __init__(self, client: GCPVectorSearchClient):
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
    """Repository for user operations"""
    
    def __init__(self, client: GCPVectorSearchClient):
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
    
    def get(self, include=None):
        """Get all messages - compatible with Chroma API"""
        # Get all documents from Firestore
        docs = self.collection.stream()
        data = {"ids": [], "metadatas": []}
        
        for doc in docs:
            doc_dict = doc.to_dict()
            data["ids"].append(doc_dict["id"])
            data["metadatas"].append(doc_dict)
            
        return data


class ConversationIndexHandle:
    """Handle for the conversations collection"""
    
    def __init__(self, collection, firestore_client):
        self.collection = collection
        self.firestore_client = firestore_client
    
    def add(self, conversation: Conversation):
        """Add a conversation to Firestore"""
        # Convert conversation to a dictionary
        conversation_dict = conversation.to_dict()
        
        # Store in Firestore
        self.collection.document(conversation.id).set(conversation_dict)
    
    def get(self, conversation_id: str = None) -> Optional[Conversation]:
        """Get a conversation by ID or get all conversations"""
        if conversation_id:
            # Get from Firestore
            doc_ref = self.collection.document(conversation_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
                
            return Conversation.from_dict(doc.to_dict())
        else:
            # Get all conversations (for compatibility with Chroma API)
            docs = self.collection.stream()
            data = {"ids": [], "metadatas": []}
            
            for doc in docs:
                doc_dict = doc.to_dict()
                data["ids"].append(doc_dict["id"])
                data["metadatas"].append(doc_dict)
                
            return data
    
    def delete(self, ids: List[str] = None):
        """Delete conversations by ID"""
        if not ids:
            return
            
        # Delete from Firestore
        batch = self.firestore_client.batch()
        for id in ids:
            batch.delete(self.collection.document(id))
        batch.commit()


class UserIndexHandle:
    """Handle for the users index and collection"""
    
    def __init__(
        self, 
        collection, 
        index_endpoint, 
        index,
        dimensions: int,
        firestore_client
    ):
        self.collection = collection
        self.index_endpoint = index_endpoint
        self.index = index
        self.dimensions = dimensions
        self.firestore_client = firestore_client
    
    def add(self, user: UserProfile):
        """Add a user to the index and Firestore"""
        # Convert user to a dictionary
        user_dict = user.to_dict()
        
        # Store in Firestore
        self.collection.document(user.id).set(user_dict)
        
        # Add to vector index if embedding exists
        if user.embedding:
            self.index.upsert_embeddings(
                embeddings=[user.embedding],
                ids=[user.id],
                metadata_list=[{
                    "id": user.id,
                    "name": user.name,
                    "discord_id": user.discord_id
                }]
            )
        else:
            logger.warning(f"No embedding for user {user.id}, skipping vector index")
    
    def get(self, user_id: str = None) -> Optional[Union[UserProfile, Dict[str, Any]]]:
        """Get a user by ID or get all users"""
        if user_id:
            # Get from Firestore
            doc_ref = self.collection.document(user_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
                
            return UserProfile.from_dict(doc.to_dict())
        else:
            # Get all users (for compatibility with Chroma API)
            docs = self.collection.stream()
            data = {"ids": [], "metadatas": []}
            
            for doc in docs:
                doc_dict = doc.to_dict()
                data["ids"].append(doc_dict["id"])
                data["metadatas"].append(doc_dict)
                
            return data
    
    def get_by_discord_id(self, discord_id: str) -> Optional[UserProfile]:
        """Get a user by Discord ID"""
        # Query Firestore
        query = self.collection.where("discord_id", "==", discord_id)
        docs = list(query.stream())
        
        if not docs:
            return None
            
        return UserProfile.from_dict(docs[0].to_dict())
    
    def update(self, user: UserProfile):
        """Update a user in the index and Firestore"""
        # Convert user to a dictionary
        user_dict = user.to_dict()
        
        # Update in Firestore
        self.collection.document(user.id).set(user_dict)
        
        # Update in vector index if embedding exists
        if user.embedding:
            self.index.upsert_embeddings(
                embeddings=[user.embedding],
                ids=[user.id],
                metadata_list=[{
                    "id": user.id,
                    "name": user.name,
                    "discord_id": user.discord_id
                }]
            )
    
    def delete(self, ids: List[str] = None):
        """Delete users by ID"""
        if not ids:
            return
            
        # Delete from Firestore
        batch = self.firestore_client.batch()
        for id in ids:
            batch.delete(self.collection.document(id))
        batch.commit()
        
        # Delete from vector index
        self.index.remove_embeddings(ids=ids)
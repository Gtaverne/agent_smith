# src/skills/embedding/service.py
from dataclasses import dataclass
from typing import List, Union, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer

from src.core.types import Message, UserProfile
from src.orchestration.services.registry import ServiceProtocol
from src.core.logger import logger
import os


@dataclass
class EmbeddingService(ServiceProtocol):
    """Service for creating embeddings from text"""
    model_name: str = "all-MiniLM-L6-v2"  # This model produces 384-dim embeddings
    
    def __post_init__(self):
        logger.info(f"Initializing embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        self.vector_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding model initialized with dimension: {self.vector_dim}")
        
        # Check if dimensions match environment setting
        env_dim = int(os.getenv('EMBEDDING_DIMENSION', '384'))
        if self.vector_dim != env_dim:
            logger.warning(f"Model dimension ({self.vector_dim}) doesn't match EMBEDDING_DIMENSION ({env_dim}) in environment!")
    
    def execute(self, text: str, **kwargs) -> List[float]:
        """Create embedding for a text string"""
        logger.info(f"Creating embedding for text: {text[:50]}...")
        embedding = self.model.encode(text)
        return embedding.tolist()  # Convert numpy array to list
    
    def embed_message(self, message: Message) -> Message:
        """Add embedding to a message"""
        if not message.embedding:
            message.embedding = self.execute(message.content)
            logger.info(f"Created embedding for message {message.id}")
        return message
    
    def embed_user(self, user: UserProfile) -> UserProfile:
        """Add embedding to a user profile based on interests"""
        if not user.embedding:
            # Create a representative text from user data
            text = f"{user.name} {' '.join(user.interests)}"
            user.embedding = self.execute(text)
            logger.info(f"Created embedding for user {user.id}")
        return user
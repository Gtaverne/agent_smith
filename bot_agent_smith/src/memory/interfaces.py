from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from src.core.types import Message, UserProfile

class VectorDBClient(ABC):
    """Abstract base class for vector database clients"""
    
    @abstractmethod
    def get_messages(self, **kwargs) -> Dict[str, Any]:
        """Get messages collection data"""
        pass
    
    @abstractmethod
    def get_users(self, **kwargs) -> Dict[str, Any]:
        """Get users collection data"""
        pass
    
    @abstractmethod
    def get_conversations(self, **kwargs) -> Dict[str, Any]:
        """Get conversations collection data"""
        pass

class MessageRepository(ABC):
    """Abstract base class for message repositories"""
    
    @abstractmethod
    def add(self, message: Message) -> None:
        """Add a message to the repository"""
        pass
    
    @abstractmethod
    def get(self, message_id: str) -> Optional[Message]:
        """Get a message by ID"""
        pass
    
    @abstractmethod
    def get_by_conversation(self, conversation_id: str) -> List[Message]:
        """Get all messages in a conversation"""
        pass
    
    @abstractmethod
    def search(self, query: str, n_results: int = 10) -> List[Message]:
        """Search for messages similar to the query"""
        pass

class UserRepository(ABC):
    """Abstract base class for user repositories"""
    
    @abstractmethod
    def add(self, user: UserProfile) -> None:
        """Add a user to the repository"""
        pass
    
    @abstractmethod
    def get(self, user_id: str) -> Optional[UserProfile]:
        """Get a user by ID"""
        pass
    
    @abstractmethod
    def get_by_discord_id(self, discord_id: str) -> Optional[UserProfile]:
        """Get a user by Discord ID"""
        pass
    
    @abstractmethod
    def update(self, user: UserProfile) -> None:
        """Update a user in the repository"""
        pass
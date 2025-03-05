from chromadb import HttpClient
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.core.types import Message, Conversation, UserProfile, Author

class ChromaClient:
    def __init__(self, host: str = "localhost", port: int = 8184):
        self.client = HttpClient(
            host=host,
            port=port,
            settings=Settings(chroma_client_auth_credentials="admin:admin")
        )
        
        # Initialize collections
        self.messages = self.client.get_or_create_collection(
            name="messages",
            metadata={"description": "Stored messages with embeddings"}
        )
        
        self.conversations = self.client.get_or_create_collection(
            name="conversations",
            metadata={"description": "Stored conversations"}
        )
        
        self.users = self.client.get_or_create_collection(
            name="users",
            metadata={"description": "User profiles"}
        )

class MessageRepository:
    def __init__(self, client: ChromaClient):
        self.client = client
        self.collection = client.messages
    
    def add(self, message: Message):
        metadata = {
            "id": message.id,
            "content": message.content,
            "type": message.type.value,
            "author_id": message.author.id,
            "author_name": message.author.name,
            "author_discord_id": message.author.discord_id,
            "timestamp": message.timestamp.isoformat(),
            "conversation_id": message.conversation_id,
            "attachments": ",".join(message.attachments)  # Convert list to string
        }
        if message.embedding:
            metadata["embedding_dim"] = len(message.embedding)
            
        self.collection.add(
            ids=[message.id],
            embeddings=[message.embedding] if message.embedding else None,
            documents=[message.content],
            metadatas=[metadata]
        )
    
    def get(self, message_id: str) -> Optional[Message]:
        result = self.collection.get(
            ids=[message_id],
            include=["metadatas", "documents"]
        )
        
        if not result["ids"]:
            return None
            
        return Message.from_dict(result["metadatas"][0])
    
    def get_by_conversation(self, conversation_id: str) -> List[Message]:
        result = self.collection.get(
            where={"conversation_id": conversation_id},
            include=["metadatas", "documents"]
        )
        
        return [Message.from_dict(metadata) for metadata in result["metadatas"]]
    
    def search(self, query: str, n_results: int = 10) -> List[Message]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["metadatas", "documents"]
        )
        
        return [Message.from_dict(metadata) for metadata in results["metadatas"][0]]

class UserRepository:
    def __init__(self, client: ChromaClient):
        self.client = client
        self.collection = client.users
    
    def add(self, user: UserProfile):
        metadata = {
            "id": user.id,
            "name": user.name,
            "discord_id": user.discord_id,
            "interests": ",".join(user.interests),  # Convert list to string
            "conversation_ids": ",".join(user.conversation_ids),  # Convert list to string
            "created_at": user.created_at.isoformat(),
            "last_interaction": user.last_interaction.isoformat()
        }
        if user.embedding:
            metadata["embedding_dim"] = len(user.embedding)
            
        self.collection.add(
            ids=[user.id],
            embeddings=[user.embedding] if user.embedding else None,
            documents=[user.name],
            metadatas=[metadata]
        )
    
    def get(self, user_id: str) -> Optional[UserProfile]:
        result = self.collection.get(
            ids=[user_id],
            include=["metadatas", "documents", "embeddings"]
        )
        
        if not result["ids"]:
            return None
            
        metadata = result["metadatas"][0]
        return UserProfile(
            id=metadata["id"],
            name=metadata["name"],
            discord_id=metadata["discord_id"],
            interests=metadata["interests"].split(",") if metadata.get("interests") else [],
            conversation_ids=metadata["conversation_ids"].split(",") if metadata.get("conversation_ids") else [],
            created_at=datetime.fromisoformat(metadata["created_at"]),
            last_interaction=datetime.fromisoformat(metadata["last_interaction"]),
            embedding=result.get("embeddings", [None])[0]
        )
    
    def get_by_discord_id(self, discord_id: str) -> Optional[UserProfile]:
        result = self.collection.get(
            where={"discord_id": discord_id},
            include=["metadatas", "documents"]
        )
        
        if not result["ids"]:
            return None
            
        return UserProfile.from_dict(result["metadatas"][0])
    
    def update(self, user: UserProfile):
        self.collection.update(
            ids=[user.id],
            embeddings=[user.embedding] if user.embedding else None,
            documents=[user.name],
            metadatas=[{
                **user.to_dict(),
                "created_at": user.created_at.isoformat(),
                "last_interaction": user.last_interaction.isoformat()
            }]
        )
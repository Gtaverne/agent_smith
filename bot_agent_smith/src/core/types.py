from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC
from enum import Enum
import uuid

class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    SYSTEM = "system"
    AUDIO = "audio"
    FILE = "file"

class SkillType(Enum):
    CONVERSATION = "conversation"
    VISION = "vision"
    WEB = "web"
    REASONING = "reasoning"

@dataclass
class Author:
    id: str
    name: str
    discord_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # Flatten the author data
        return {
            "author_id": self.id,
            "author_name": self.name,
            "author_discord_id": self.discord_id,
        }

@dataclass
class Message:
    content: str
    type: MessageType
    author: Author
    conversation_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    attachments: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # Flatten the entire structure
        return {
            "id": self.id,
            "content": self.content,
            "type": self.type.value,
            **self.author.to_dict(),  # Flatten author fields
            "timestamp": self.timestamp.isoformat(),
            "conversation_id": self.conversation_id,
            "attachments": ",".join(self.attachments),
            "embedding": self.embedding,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        # Create author from flat data
        author = Author(
            id=data["author_id"],
            name=data["author_name"],
            discord_id=data.get("author_discord_id"),
        )
        
        return cls(
            id=data["id"],
            content=data["content"],
            type=MessageType(data["type"]),
            author=author,
            timestamp=datetime.fromisoformat(data["timestamp"]),
            conversation_id=data["conversation_id"],
            attachments=data["attachments"].split(",") if data.get("attachments") else [],
            embedding=data.get("embedding"),
        )

@dataclass
class Conversation:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Message] = field(default_factory=list)
    participants: List[Author] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_message_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: Message):
        self.messages.append(message)
        self.last_message_at = message.timestamp
        
        if message.author not in self.participants:
            self.participants.append(message.author)

    def to_dict(self) -> Dict[str, Any]:
        # Flatten the conversation data
        return {
            "id": self.id,
            "participants_ids": ",".join(p.id for p in self.participants),
            "participants_names": ",".join(p.name for p in self.participants),
            "participants_discord_ids": ",".join(str(p.discord_id) for p in self.participants if p.discord_id),
            "created_at": self.created_at.isoformat(),
            "last_message_at": self.last_message_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        # Reconstruct participants from flat data
        participant_ids = data["participants_ids"].split(",") if data.get("participants_ids") else []
        participant_names = data["participants_names"].split(",") if data.get("participants_names") else []
        participant_discord_ids = data["participants_discord_ids"].split(",") if data.get("participants_discord_ids") else []
        
        # Pad discord_ids with None if necessary
        participant_discord_ids.extend([None] * (len(participant_ids) - len(participant_discord_ids)))
        
        participants = [
            Author(id=pid, name=name, discord_id=did)
            for pid, name, did in zip(participant_ids, participant_names, participant_discord_ids)
        ]
        
        return cls(
            id=data["id"],
            participants=participants,
            created_at=datetime.fromisoformat(data["created_at"]),
            last_message_at=datetime.fromisoformat(data["last_message_at"]),
        )

@dataclass
class UserProfile:
    id: str
    name: str
    discord_id: str
    interests: List[str] = field(default_factory=list)
    conversation_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_interaction: datetime = field(default_factory=lambda: datetime.now(UTC))
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # Flatten the user profile data
        return {
            "id": self.id,
            "name": self.name,
            "discord_id": self.discord_id,
            "interests": ",".join(self.interests),
            "conversation_ids": ",".join(self.conversation_ids),
            "created_at": self.created_at.isoformat(),
            "last_interaction": self.last_interaction.isoformat(),
            "embedding": self.embedding,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        return cls(
            id=data["id"],
            name=data["name"],
            discord_id=data["discord_id"],
            interests=data["interests"].split(",") if data.get("interests") else [],
            conversation_ids=data["conversation_ids"].split(",") if data.get("conversation_ids") else [],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_interaction=datetime.fromisoformat(data["last_interaction"]),
            embedding=data.get("embedding"),
        )
    
@dataclass
class AgentResponse:
    """Response from the agent containing one or more messages"""
    messages: List[Dict[str, str]]  # List of message contents
    needs_acknowledgment: bool = False  # Flag for immediate acknowledgment
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def single_message(cls, content: str) -> 'AgentResponse':
        """Create a response with a single message"""
        return cls(messages=[{"content": content}])
    
    @classmethod
    def with_acknowledgment(cls, acknowledgment_text: str, processing: bool = True) -> 'AgentResponse':
        """Create a response with an acknowledgment that more is coming"""
        response = cls(messages=[{"content": acknowledgment_text}], needs_acknowledgment=True)
        response.metadata["processing"] = processing
        return response
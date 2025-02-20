from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, UTC

from src.core.types import Message, UserProfile
from src.orchestration.services.registry import ServiceProtocol
from src.memory.chroma import MessageRepository, UserRepository

@dataclass
class ContextMetadata:
    """Metadata about the context"""
    last_updated: datetime
    window_size: int
    ttl: timedelta

@dataclass
class ContextWindow:
    """A window of conversation context"""
    conversation_id: str
    messages: List[Message]
    user_profile: Optional[UserProfile]
    metadata: ContextMetadata

    def is_stale(self) -> bool:
        """Check if the context needs to be refreshed"""
        return datetime.now(UTC) - self.metadata.last_updated > self.metadata.ttl

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to a format suitable for LLM input"""
        # Deduplicate messages based on content and adjacent timestamps
        deduped_messages = []
        for msg in self.messages:
            if not deduped_messages or deduped_messages[-1].content != msg.content:
                deduped_messages.append(msg)

        return {
            "conversation_id": self.conversation_id,
            "messages": [
                {
                    "role": "assistant" if msg.author.discord_id.startswith("bot_") else "user",
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in deduped_messages
            ],
            "user": {
                "name": self.user_profile.name,
                "interests": self.user_profile.interests
            } if self.user_profile else None,
            "metadata": {
                "last_updated": self.metadata.last_updated.isoformat(),
                "window_size": self.metadata.window_size,
                "ttl_minutes": self.metadata.ttl.total_seconds() / 60
            }
        }

@dataclass
class ContextService(ServiceProtocol):
    """Service for managing conversation context"""
    message_repository: MessageRepository
    user_repository: UserRepository
    window_size: int = 10
    ttl: timedelta = timedelta(minutes=30)
    max_windows: int = 20
    
    def __post_init__(self):
        self.active_windows: Dict[str, ContextWindow] = {}

    def execute(self, message: Message) -> Dict[str, Any]:
        """Get or create context window for a message"""
        window = self._get_or_create_window(
            conversation_id=message.conversation_id,
            user_id=message.author.id
        )
        window = self._add_message(window, message)
        return window.to_dict()

    def _get_or_create_window(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> ContextWindow:
        """Get existing window or create new one"""
        # Return existing window if not stale
        if conversation_id in self.active_windows:
            window = self.active_windows[conversation_id]
            if not window.is_stale():
                return window

        # Fetch recent messages
        messages = self.message_repository.get_by_conversation(conversation_id)
        messages = sorted(messages, key=lambda m: m.timestamp)[-self.window_size:]

        # Fetch user profile if provided
        user_profile = None
        if user_id:
            user_profile = self.user_repository.get(user_id)

        # Create metadata
        metadata = ContextMetadata(
            last_updated=datetime.now(UTC),
            window_size=self.window_size,
            ttl=self.ttl
        )

        # Create new window
        window = ContextWindow(
            conversation_id=conversation_id,
            messages=messages,
            user_profile=user_profile,
            metadata=metadata
        )

        # Manage active windows limit
        if len(self.active_windows) >= self.max_windows:
            oldest_id = min(
                self.active_windows.keys(),
                key=lambda k: self.active_windows[k].metadata.last_updated
            )
            del self.active_windows[oldest_id]

        self.active_windows[conversation_id] = window
        return window

    def _add_message(self, window: ContextWindow, message: Message) -> ContextWindow:
        """Add a message to the context window"""
        window.messages.append(message)
        if len(window.messages) > window.metadata.window_size:
            window.messages = window.messages[-window.metadata.window_size:]
        window.metadata.last_updated = datetime.now(UTC)
        return window
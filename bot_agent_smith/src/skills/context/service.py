from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, UTC

from src.core.types import Message, UserProfile
from src.orchestration.services.registry import ServiceProtocol
from src.memory.chroma import MessageRepository, UserRepository
from src.core.logger import logger

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
        # Only use recent messages from the same conversation
        conversation_messages = sorted(self.messages, key=lambda m: m.timestamp)
        
        # Deduplicate messages based on content and timestamp
        deduped_messages = []
        for msg in conversation_messages:
            # Skip if nearly duplicate of previous message
            if deduped_messages and self._is_duplicate(msg, deduped_messages[-1]):
                continue
            deduped_messages.append(msg)
        
        # Use only the last few messages
        recent_messages = deduped_messages[-self.metadata.window_size:]
        
        return {
            "conversation_id": self.conversation_id,
            "messages": [
                {
                    "role": "assistant" if msg.author.discord_id and msg.author.discord_id.startswith("bot_") else "user",
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in recent_messages
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
    
    def _is_duplicate(self, msg1: Message, msg2: Message) -> bool:
        """Check if two messages are very similar (duplicates)"""
        content_match = msg1.content == msg2.content
        author_match = msg1.author.id == msg2.author.id
        time_close = abs((msg1.timestamp - msg2.timestamp).total_seconds()) < 5
        return content_match and author_match and time_close

@dataclass
class ContextService(ServiceProtocol):
    """Service for managing conversation context"""
    message_repository: MessageRepository
    user_repository: UserRepository
    window_size: int = 5  # Reduced window size to avoid too much context
    ttl: timedelta = timedelta(minutes=10)  # Shorter TTL to avoid stale contexts
    max_windows: int = 20
    
    def __post_init__(self):
        self.active_windows: Dict[str, ContextWindow] = {}

    def execute(self, message: Message, **kwargs) -> Dict[str, Any]:
        """Get or create context window for a message"""
        logger.info(f"Getting context for conversation: {message.conversation_id}")
        window = self._get_or_create_window(
            conversation_id=message.conversation_id,
            user_id=message.author.id
        )
        window = self._add_message(window, message)
        context_dict = window.to_dict()
        
        # Log context messages for debugging
        logger.info(f"Context contains {len(context_dict['messages'])} messages")
        for i, msg in enumerate(context_dict['messages']):
            logger.info(f"Context message {i+1}: {msg['role']}: {msg['content'][:50]}...")
        
        return context_dict

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

        # Fetch recent messages for this specific conversation only
        logger.info(f"Creating new context window for conversation: {conversation_id}")
        messages = self.message_repository.get_by_conversation(conversation_id)
        
        # Only use messages from the last hour to avoid old context
        recent_time = datetime.now(UTC) - timedelta(hours=1)
        recent_messages = [m for m in messages if m.timestamp > recent_time]
        
        # Sort by timestamp and limit to window size
        sorted_messages = sorted(recent_messages, key=lambda m: m.timestamp)
        window_messages = sorted_messages[-self.window_size:] if sorted_messages else []

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
            messages=window_messages,
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
        # Check if the message is a duplicate
        for existing in window.messages:
            if window._is_duplicate(message, existing):
                logger.info(f"Skipping duplicate message: {message.content[:50]}...")
                return window
                
        # Add message and update window
        window.messages.append(message)
        if len(window.messages) > window.metadata.window_size * 2:  # Allow buffer
            # Sort by timestamp and keep most recent
            window.messages = sorted(window.messages, key=lambda m: m.timestamp)
            window.messages = window.messages[-window.metadata.window_size:]
            
        window.metadata.last_updated = datetime.now(UTC)
        return window
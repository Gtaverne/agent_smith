from typing import Dict, Optional

from agent_smith.bot_agent_smith.src.memory.chroma_db.chroma import MessageRepository, UserRepository
from src.core.types import Message
from .window import ConversationWindow

class ConversationManager:
    def __init__(
        self,
        message_repository: MessageRepository,
        user_repository: UserRepository,
        window_size: int = 10,
        max_windows: int = 20
    ):
        self.message_repository = message_repository
        self.user_repository = user_repository
        self.window_size = window_size
        self.max_windows = max_windows
        self.active_windows: Dict[str, ConversationWindow] = {}

    def get_or_create_window(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> ConversationWindow:
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

        # Create new window
        window = ConversationWindow(
            conversation_id=conversation_id,
            messages=messages,
            user_profile=user_profile,
            window_size=self.window_size
        )

        # Manage active windows limit
        if len(self.active_windows) >= self.max_windows:
            oldest_id = min(
                self.active_windows.keys(),
                key=lambda k: self.active_windows[k].last_updated
            )
            del self.active_windows[oldest_id]

        self.active_windows[conversation_id] = window
        return window

    def add_message(self, message: Message) -> ConversationWindow:
        window = self.get_or_create_window(
            message.conversation_id,
            message.author.id
        )
        window.add_message(message)
        return window

    def get_context(self, conversation_id: str) -> Optional[Dict]:
        """Get the current context for a conversation"""
        window = self.active_windows.get(conversation_id)
        return window.get_context() if window else None
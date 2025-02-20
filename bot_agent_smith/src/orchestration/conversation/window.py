from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime, timedelta, UTC

from src.core.types import Message, UserProfile

@dataclass
class ConversationWindow:
    conversation_id: str
    messages: List[Message]
    user_profile: Optional[UserProfile]
    window_size: int = 10
    context_ttl: timedelta = timedelta(minutes=30)
    last_updated: datetime = datetime.now(UTC)

    def is_stale(self) -> bool:
        return datetime.now(UTC) - self.last_updated > self.context_ttl

    def add_message(self, message: Message):
        self.messages.append(message)
        if len(self.messages) > self.window_size:
            self.messages = self.messages[-self.window_size:]
        self.last_updated = datetime.now(UTC)

    def get_context(self) -> Dict:
        """Returns the current conversation context in a format suitable for LLM input"""
        # First, let's deduplicate messages based on content and adjacent timestamps
        deduped_messages = []
        for msg in self.messages:
            if not deduped_messages or \
               deduped_messages[-1].content != msg.content:
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
            } if self.user_profile else None
        }
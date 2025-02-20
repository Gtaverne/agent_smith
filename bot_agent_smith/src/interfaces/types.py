from typing import Protocol, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, UTC

class ChannelType(Enum):
    DISCORD = "discord"
    WEB = "web"
    WHATSAPP = "whatsapp"
    CLI = "cli"

@dataclass
class Channel:
    """Information about the communication channel"""
    type: ChannelType
    channel_id: str
    metadata: Dict[str, Any] = None

@dataclass
class UserInfo:
    """Information about the message sender"""
    user_id: str
    username: str
    channel_specific_id: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class CommunicationEvent:
    """A message or event from any channel"""
    content: str
    user: UserInfo
    channel: Channel
    timestamp: datetime
    event_id: str
    reply_to: Optional[str] = None
    attachments: Dict[str, Any] = None
    metadata: Dict[str, Any] = None

class ChannelAdapter(Protocol):
    """Protocol that all channel adapters must implement"""
    
    async def initialize(self) -> None:
        """Set up any necessary connections or resources"""
        ...
    
    async def start(self) -> None:
        """Start listening for events from the channel"""
        ...
    
    async def stop(self) -> None:
        """Stop listening for events and clean up"""
        ...
    
    async def send_message(self, channel_id: str, content: str, reply_to: Optional[str] = None) -> None:
        """Send a message to the channel"""
        ...
    
    async def send_error(self, channel_id: str, error: str, reply_to: Optional[str] = None) -> None:
        """Send an error message to the channel"""
        ...
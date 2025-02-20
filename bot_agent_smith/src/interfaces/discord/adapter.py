from discord import Message, Client, Intents, DMChannel, TextChannel
from typing import Optional, Protocol
from datetime import datetime, UTC

from src.core.logger import logger
from src.interfaces.types import (
    ChannelAdapter,
    ChannelType,
    Channel,
    UserInfo,
    CommunicationEvent
)

class DiscordAdapter(ChannelAdapter):
    """Discord adapter that handles Discord-specific message conversion and communication"""
    
    def __init__(self, token: str):
        self.token = token
        self.client = None
        self._message_handler: Optional[Protocol] = None
    
    def set_message_handler(self, handler: Protocol):
        """Set the function to be called when a message is received"""
        self._message_handler = handler
    
    async def initialize(self) -> None:
        """Initialize Discord client with required intents"""
        intents = Intents.default()
        intents.message_content = True
        intents.dm_messages = True
        
        self.client = Client(intents=intents)
        
        # Set up message handler
        @self.client.event
        async def on_message(message: Message):
            if message.author == self.client.user:
                return
                
            logger.info(f"Discord message received from {message.author}: {message.content}")
            
            if self._message_handler:
                event = self.convert_message(message)
                await self._message_handler(event)
    
    async def start(self) -> None:
        """Start the Discord client"""
        await self.client.start(self.token)
    
    async def stop(self) -> None:
        """Stop the Discord client"""
        if self.client:
            await self.client.close()
    
    async def send_message(self, channel_id: str, content: str, reply_to: Optional[str] = None) -> None:
        """Send a message to a Discord channel"""
        logger.info(f"Attempting to send message to channel {channel_id}: {content[:100]}...")
        
        # Try getting the channel directly first
        channel = self.client.get_channel(int(channel_id))
        
        # If channel not found, it might be a DM - fetch the user and create DM channel
        if not channel:
            try:
                user = await self.client.fetch_user(int(channel_id))
                channel = await user.create_dm()
            except Exception as e:
                logger.error(f"Failed to get channel or create DM: {str(e)}")
                return
        
        if not channel:
            logger.error(f"Could not find channel or create DM for ID: {channel_id}")
            return
            
        logger.info(f"Found channel: {channel.__class__.__name__}")
        
        try:
            if reply_to:
                # Fetch and reply to the original message
                message = await channel.fetch_message(int(reply_to))
                await message.reply(content)
                logger.info(f"Sent reply to message {reply_to}")
            else:
                # Send new message
                await channel.send(content)
                logger.info("Sent new message")
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
    
    def convert_message(self, message: Message) -> CommunicationEvent:
        """Convert a Discord message to a CommunicationEvent"""
        # For DMs, use the user's ID as the channel ID
        channel_id = str(message.author.id) if isinstance(message.channel, DMChannel) else str(message.channel.id)
        
        channel = Channel(
            type=ChannelType.DISCORD,
            channel_id=channel_id,
            metadata={
                "guild_id": str(message.guild.id) if message.guild else None,
                "channel_name": message.channel.name if hasattr(message.channel, 'name') else "DM",
                "is_dm": isinstance(message.channel, DMChannel)
            }
        )
        
        user = UserInfo(
            user_id=str(message.author.id),
            username=message.author.name,
            channel_specific_id=str(message.author.id)
        )
        
        attachments = {
            att.filename: {
                "url": att.url,
                "content_type": att.content_type,
                "size": att.size
            }
            for att in message.attachments
        }
        
        return CommunicationEvent(
            content=message.content,
            user=user,
            channel=channel,
            timestamp=message.created_at or datetime.now(UTC),
            event_id=str(message.id),
            reply_to=str(message.reference.message_id) if message.reference else None,
            attachments=attachments
        )
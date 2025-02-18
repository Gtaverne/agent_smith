from discord import Client, Message, Intents, DMChannel
from discord.ext import commands
from typing import Optional, Any
from datetime import datetime
from src.core import logger

from src.interfaces.types import (
    ChannelAdapter,
    ChannelType,
    Channel,
    UserInfo,
    CommunicationEvent
)

class DiscordAdapter(ChannelAdapter):
    """Simple Discord adapter that handles Discord-specific message conversion"""
    
    def __init__(self, token: str):
        self.token = token
        
        # Set up Discord client
        intents = Intents.default()
        intents.message_content = True
        intents.dm_messages = True
        
        self.client = commands.Bot(command_prefix="!", intents=intents)
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.client.event
        async def on_ready():
            logger.info(f"Discord adapter logged in as {self.client.user}")

        @self.client.event
        async def on_message(message: Message):
            # Ignore messages from the bot itself
            if message.author == self.client.user:
                return
            
            # Get channel info - handle both DM and regular channels
            channel_info = "DM" if isinstance(message.channel, DMChannel) else f"channel #{message.channel.name}"
            logger.info(f"Received Discord message from {message.author.name} in {channel_info}")
            logger.debug(f"Message content: {message.content[:100]}...")
    
    async def initialize(self) -> None:
        """Nothing special needed for Discord initialization"""
        pass
    
    async def start(self) -> None:
        """Start the Discord client"""
        await self.client.start(self.token)
    
    async def stop(self) -> None:
        """Stop the Discord client"""
        await self.client.close()
    
    async def send_message(self, channel_id: str, content: str, reply_to: Optional[str] = None) -> None:
        """Send a message to a Discord channel"""
        channel = self.client.get_channel(int(channel_id))
        if channel:
            if reply_to:
                try:
                    reply_msg = await channel.fetch_message(int(reply_to))
                    await reply_msg.reply(content)
                except:
                    await channel.send(content)
            else:
                await channel.send(content)
            logger.debug(f"Sent message to channel {channel_id}")
    
    async def send_error(self, channel_id: str, error: str, reply_to: Optional[str] = None) -> None:
        """Send an error message to a Discord channel"""
        error_message = f"Error: {error}"
        await self.send_message(channel_id, error_message, reply_to)
    
    def _convert_to_event(self, message: Message) -> CommunicationEvent:
        """Convert a Discord message to a CommunicationEvent"""
        channel = Channel(
            type=ChannelType.DISCORD,
            channel_id=str(message.channel.id),
            metadata={
                "guild_id": str(message.guild.id) if message.guild else None,
                "channel_name": message.channel.name if hasattr(message.channel, 'name') else "DM"
            }
        )
        
        user = UserInfo(
            user_id=str(message.author.id),
            username=message.author.name,
            channel_specific_id=str(message.author.id),
            metadata={
                "discriminator": message.author.discriminator,
                "bot": message.author.bot
            }
        )
        
        attachments = {}
        if message.attachments:
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
            timestamp=message.created_at or datetime.utcnow(),
            event_id=str(message.id),
            reply_to=str(message.reference.message_id) if message.reference else None,
            attachments=attachments,
            metadata={
                "embeds": [embed.to_dict() for embed in message.embeds],
                "pinned": message.pinned,
                "mention_everyone": message.mention_everyone
            }
        )
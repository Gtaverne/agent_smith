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
    DISCORD_MSG_LIMIT = 2000  # Discord's message length limit
    CHUNK_MARKER_TEMPLATE = "\n[Part {}/{}]"  # Format for chunk markers
    SECTION_DELIMITERS = [
        "\n\n**",  # Major section headers
        "\n**",    # Secondary section headers
        "\n\n",    # Double newline between paragraphs
        "\n",      # Single newline (last resort)
    ]    
    
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
        """Send a message to a Discord channel, chunking if necessary"""
        logger.info(f"Attempting to send message to channel {channel_id}: {content[:100]}...")
        
        # Get channel
        channel = self.client.get_channel(int(channel_id))
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
        
        # Chunk the message
        chunks = self._chunk_message(content)
        
        # Send each chunk
        for i, chunk in enumerate(chunks):
            formatted_chunk = self._format_chunk(chunk, i, len(chunks))
            try:
                if reply_to and i == 0:  # Only reply with the first chunk
                    message = await channel.fetch_message(int(reply_to))
                    await message.reply(formatted_chunk)
                    logger.info(f"Sent first chunk as reply to message {reply_to}")
                else:
                    await channel.send(formatted_chunk)
                    logger.info(f"Sent chunk {i + 1}/{len(chunks)}")
            except Exception as e:
                logger.error(f"Failed to send message chunk {i + 1}/{len(chunks)}: {str(e)}")
    
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
            reply_to=str(message.reference.message_id) if message.reference  else None,
            attachments=attachments
        )
    
    def _find_best_split_point(self, content: str, limit: int) -> int:
        """
        Find the best point to split content, prioritizing:
        1. Section headers
        2. Paragraph breaks
        3. Complete markdown blocks
        """
        for delimiter in self.SECTION_DELIMITERS:
            # Look for delimiter within limit
            last_position = content[:limit].rfind(delimiter)
            if last_position > 0:
                return last_position
                
        # If no natural delimiter found, try to avoid splitting markdown
        # Look backwards from limit for ** to ensure we don't split bold text
        markdown_end = content[:limit].rfind('**')
        markdown_start = content[:markdown_end].rfind('**') if markdown_end > 0 else -1
        
        if markdown_start >= 0 and markdown_end > markdown_start:
            # Found complete markdown block, split after it
            return markdown_end + 2
            
        # Last resort: split at last space
        last_space = content[:limit].rfind(' ')
        return last_space if last_space > 0 else limit

    def _chunk_message(self, content: str) -> list[str]:
        """
        Split a message into chunks that respect both Discord's length limit
        and content structure.
        """
        if len(content) <= self.DISCORD_MSG_LIMIT:
            return [content]
            
        chunks = []
        remaining = content
        
        while remaining:
            # Calculate space needed for chunk marker
            marker_space = len(self.CHUNK_MARKER_TEMPLATE.format(1, 1))
            available_space = self.DISCORD_MSG_LIMIT - marker_space
            
            if len(remaining) <= available_space:
                chunks.append(remaining)
                break
                
            # Find best split point
            split_point = self._find_best_split_point(remaining, available_space)
            
            # Add chunk and continue with remaining content
            chunks.append(remaining[:split_point].strip())
            remaining = remaining[split_point:].strip()
            
            # If we can't make progress, force a split
            if not remaining:
                break
                
        return chunks

    def _format_chunk(self, chunk: str, index: int, total: int) -> str:
        """
        Format a chunk by adding the part indicator.
        """
        # Only add markers if there are multiple chunks
        if total > 1:
            marker = self.CHUNK_MARKER_TEMPLATE.format(index + 1, total)
            
            # Ensure chunk plus marker doesn't exceed limit
            available_space = self.DISCORD_MSG_LIMIT - len(marker)
            if len(chunk) > available_space:
                chunk = chunk[:available_space]
            
            return chunk + marker
        
        return chunk
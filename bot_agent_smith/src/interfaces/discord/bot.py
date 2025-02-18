from discord.ext import commands
from discord import Intents, Message, DMChannel
import os
import uuid

from src.core.agent import Agent
from src.interfaces.discord.adapter import DiscordAdapter
from src.interfaces.types import ChannelType
from src.memory.chroma import ChromaClient, MessageRepository, UserRepository
from src.orchestration.services.registry import ServiceRegistry
from src.skills.context.service import ContextService
from src.core.logger import logger

class AgentSmithBot(commands.Bot):
    def __init__(self):
        # Set up Discord intents
        intents = Intents.default()
        intents.message_content = True
        intents.dm_messages = True
        super().__init__(command_prefix="!", intents=intents)
        
        logger.info("Initializing AgentSmithBot...")
        
        # Initialize core components
        self.service_registry = ServiceRegistry()
        self.chroma = ChromaClient(
            host=os.getenv('CHROMA_HOST', 'localhost'),
            port=int(os.getenv('CHROMA_PORT', '8184'))
        )
        self.message_repository = MessageRepository(self.chroma)
        self.user_repository = UserRepository(self.chroma)
        
        # Initialize context service
        context_service = ContextService(
            message_repository=self.message_repository,
            user_repository=self.user_repository
        )
        self.service_registry.register(
            name="context",
            service=context_service,
            description="Manages conversation context windows",
            version="1.0.0"
        )
        
        # Initialize agent
        self.agent = Agent(
            service_registry=self.service_registry,
            message_repository=self.message_repository,
            user_repository=self.user_repository,
            name="Agent Smith",
            agent_id=str(uuid.uuid4())
        )
        
        # Initialize Discord adapter
        self.discord_adapter = DiscordAdapter(os.getenv('DISCORD_TOKEN'))
        self.agent.register_adapter(ChannelType.DISCORD.value, self.discord_adapter)

    async def setup_hook(self):
        """Called when the bot is setting up"""
        await self.tree.sync()
        await self.agent.start()
        logger.info("Bot setup completed, synced application commands")
        
    async def close(self):
        """Called when the bot is shutting down"""
        await self.agent.stop()
        await super().close()
        
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("Bot is ready to receive messages")
        
    async def handle_dm(self, message: Message):
        """Handle direct messages sent to the bot"""
        # Convert Discord message to CommunicationEvent
        event = await self.discord_adapter.convert_to_event(message)
        logger.info(f"Processing direct message from {message.author.name}")
        
        # Let the agent handle the event
        response = await self.agent.handle_event(event)
        
        if response:
            # Send response back to user
            await message.channel.send(response)
            logger.debug("Sent response to user")
            
    async def on_message(self, message: Message):
        """Called when the bot receives a message"""
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
            
        # Log basic message info
        channel_type = "DM" if isinstance(message.channel, DMChannel) else "server"
        channel_name = message.channel.name if hasattr(message.channel, 'name') else "Direct Message"
        
        logger.info(f"Bot received {channel_type} message in {channel_name}")
        logger.info(f"From: {message.author.name} (ID: {message.author.id})")
        logger.debug(f"Content: {message.content[:100]}...")
        
        if message.attachments:
            logger.info(f"Message has {len(message.attachments)} attachments")
            for att in message.attachments:
                logger.debug(f"Attachment: {att.filename} ({att.content_type})")
            
        # Handle DMs
        if isinstance(message.channel, DMChannel):
            logger.info(f"Processing direct message from {message.author.name}")
            await self.handle_dm(message)
        
        # Process commands (if any)
        await self.process_commands(message)    
    
    
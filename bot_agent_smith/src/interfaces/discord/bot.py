# src/interfaces/discord/bot.py

from discord.ext import commands
from discord import Intents
import uuid
import os

from src.core.logger import logger
from src.core.agent import Agent
from src.interfaces.discord.adapter import DiscordAdapter
from src.interfaces.types import ChannelType
from src.memory.chroma import ChromaClient, MessageRepository, UserRepository
from src.orchestration.services.registry import ServiceRegistry

class AgentSmithBot(commands.Bot):
    def __init__(self):
        # Set up Discord intents
        intents = Intents.default()
        intents.message_content = True
        intents.dm_messages = True
        super().__init__(command_prefix="!", intents=intents)
        
        # Initialize core components
        self.service_registry = ServiceRegistry()
        self.chroma = ChromaClient(
            host=os.getenv('CHROMA_HOST', 'localhost'),
            port=int(os.getenv('CHROMA_PORT', '8184'))
        )
        
        # Initialize repositories
        self.message_repository = MessageRepository(self.chroma)
        self.user_repository = UserRepository(self.chroma)
        
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
        
        # Set message handler
        self.discord_adapter.set_message_handler(self.handle_message)
        
        # Register adapter with agent
        self.agent.register_adapter(ChannelType.DISCORD.value, self.discord_adapter)

    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("Bot is starting up...")
        await self.agent.start()
        
    async def close(self):
        """Called when the bot is shutting down"""
        logger.info("Bot is shutting down...")
        await self.agent.stop()
        await super().close()
        
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f"Bot is ready! Logged in as {self.user} (ID: {self.user.id})")
    
    async def handle_message(self, event):
        """Handle incoming communication events"""
        logger.info(f"Processing message: {event.content[:100]}...")
        response = await self.agent.handle_event(event)
        
        if response:
            await self.discord_adapter.send_message(
                channel_id=event.channel.channel_id,
                content=response,
                reply_to=event.event_id
            )
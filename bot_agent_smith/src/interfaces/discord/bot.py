from discord.ext import commands
from discord import Intents
import uuid
import os
import asyncio

from src.core.logger import logger
from src.core.agent import Agent
from src.interfaces.discord.adapter import DiscordAdapter
from src.interfaces.types import ChannelType
from src.orchestration.services.registry import ServiceRegistry
from src.memory import create_vector_db_client, create_message_repository, create_user_repository

class AgentSmithBot(commands.Bot):
    def __init__(self, message_repository=None, user_repository=None):
        # Set up Discord intents
        intents = Intents.default()
        intents.message_content = True
        intents.dm_messages = True
        super().__init__(command_prefix="!", intents=intents)
        
        # Initialize core components
        self.service_registry = ServiceRegistry()
        
        # Initialize repositories if not provided
        if message_repository is None or user_repository is None:
            # Create default vector DB client and repositories
            vector_db_client = create_vector_db_client()
            self.message_repository = create_message_repository(vector_db_client)
            self.user_repository = create_user_repository(vector_db_client)
        else:
            # Use provided repositories
            self.message_repository = message_repository
            self.user_repository = user_repository
        
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
        
        # Process the event with the agent
        agent_response = await self.agent.handle_event(event)
        
        if not agent_response:
            return
        
        # Check if this is an acknowledgment that more processing will follow
        if agent_response.needs_acknowledgment:
            # Send immediate acknowledgment
            await self.discord_adapter.send_message(
                channel_id=event.channel.channel_id,
                content=agent_response.messages[0]["content"],
                reply_to=event.event_id
            )
            
            # If this is a processing ack, we need to continue with the workflow
            if agent_response.metadata.get("processing", False):
                # Continue processing in a background task
                asyncio.create_task(self._process_counter_arguments(event))
            
            return
            
        # Normal response handling
        if agent_response.messages:
            # Send each message with a small delay between them
            for i, msg_obj in enumerate(agent_response.messages):
                content = msg_obj.get("content", "")
                if content:
                    # Only reply to the original message with the first response
                    reply_to = event.event_id if i == 0 else None
                    
                    await self.discord_adapter.send_message(
                        channel_id=event.channel.channel_id,
                        content=content,
                        reply_to=reply_to
                    )
                    
                    # Add a small delay between messages
                    if i < len(agent_response.messages) - 1:
                        await asyncio.sleep(1)

    async def _process_counter_arguments(self, event):
        """Continue processing to generate counter-arguments after acknowledgment"""
        try:
            # Set up workflow input for counter-arguments
            workflow_input = {
                "message": self._event_to_agent_message(event),
                "context": {},
                "response": "",
                "needs_counter_arguments": True,  # Force counter-arguments
                "keywords": [],
                "articles": [],
                "counter_arguments": [],
                "messages_to_send": [],
                "_skip_qualification": True  # Skip qualification in workflow since we already did it
            }
            
            # Run the full counter-argument workflow
            result = self.agent.workflow.invoke(workflow_input)
            
            # Send the results
            if result and result.get("messages_to_send"):
                messages = result.get("messages_to_send")
                
                # Send each message
                for i, msg_obj in enumerate(messages):
                    content = msg_obj.get("content", "")
                    if content:
                        # Don't reply to original for these follow-up messages
                        await self.discord_adapter.send_message(
                            channel_id=event.channel.channel_id,
                            content=content,
                            reply_to=None
                        )
                        
                        # Add a small delay between messages
                        if i < len(messages) - 1:
                            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in counter-argument processing: {str(e)}")
            # Send error message if needed
            await self.discord_adapter.send_message(
                channel_id=event.channel.channel_id,
                content="I encountered an error while gathering different perspectives. Please try again.",
                reply_to=None
            )

    # Helper method for the Bot class
    def _event_to_agent_message(self, event):
        """Convert communication event to a message the agent can process"""
        return self.agent._event_to_message(event)
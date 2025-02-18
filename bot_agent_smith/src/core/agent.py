from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END

from src.interfaces.types import CommunicationEvent, ChannelAdapter
from src.core.types import Message, Author, MessageType
from src.orchestration.services.registry import ServiceRegistry
from src.memory.chroma import MessageRepository, UserRepository
from src.core.logger import logger
from src.orchestration.workflows.workflow import ConversationWorkflow
from src.orchestration.workflows.state import WorkflowState

@dataclass
class Agent:
    """
    Channel-agnostic agent that implements Model-Context-Protocol architecture
    using LangGraph for workflow orchestration
    """
    service_registry: ServiceRegistry
    message_repository: MessageRepository
    user_repository: UserRepository
    name: str
    agent_id: str
    adapters: Dict[str, ChannelAdapter] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize LangGraph workflows"""
        self.workflows = self._initialize_workflows()
    
    def _initialize_workflows(self) -> Dict[str, StateGraph]:
        """Initialize available workflows using LangGraph"""
        workflows = {}
        
        # Initialize conversation workflow
        conversation_workflow = ConversationWorkflow(
            service_registry=self.service_registry
        )
        workflows["conversation"] = conversation_workflow
        
        logger.info("Initialized LangGraph workflows")
        return workflows
    
    def register_adapter(self, channel_type: str, adapter: ChannelAdapter):
        """Register a new channel adapter"""
        self.adapters[channel_type] = adapter
        logger.info(f"Registered adapter for channel type: {channel_type}")
        
    async def start(self):
        """Start all registered adapters"""
        for channel_type, adapter in self.adapters.items():
            logger.info(f"Starting adapter for channel: {channel_type}")
            await adapter.initialize()
            await adapter.start()
            
    async def stop(self):
        """Stop all registered adapters"""
        for channel_type, adapter in self.adapters.items():
            logger.info(f"Stopping adapter for channel: {channel_type}")
            await adapter.stop()

    async def handle_event(self, event: CommunicationEvent) -> Optional[str]:
        """
        Process a communication event using LangGraph workflow
        
        This is the main entry point for the MCP architecture:
        1. Event is converted to internal message format
        2. Message is stored in context (memory)
        3. LangGraph orchestrates the processing workflow
        4. Response is returned to appropriate channel
        """
        logger.info(f"Received event from channel: {event.channel.type.value}")
        logger.debug(f"Event details: user={event.user.username}, channel_id={event.channel.channel_id}")
        
        # Convert event to internal message format
        message = self._event_to_message(event)
        logger.info(f"Converted to message: id={message.id}, conversation_id={message.conversation_id}")
        
        # Store message in context (memory)
        self.message_repository.add(message)
        logger.debug("Message stored in repository")
        
        # Initialize workflow state
        initial_state = WorkflowState(message=message)
        
        # Execute workflow through LangGraph
        workflow = self.workflows["conversation"]
        final_state = await workflow.execute(initial_state)
        
        # Create and store response if generated
        if final_state and final_state.llm_responses:
            response = final_state.llm_responses[-1]
            response_message = self._create_response_message(
                content=response,
                reply_to_message=message
            )
            self.message_repository.add(response_message)
            logger.info("Stored response message in repository")
            return response
            
        return None

    def _event_to_message(self, event: CommunicationEvent) -> Message:
        """Convert a CommunicationEvent to internal Message format"""
        author = Author(
            id=event.user.user_id,
            name=event.user.username,
            discord_id=event.user.channel_specific_id
        )
        
        return Message(
            content=event.content,
            type=MessageType.TEXT,
            author=author,
            conversation_id=event.channel.channel_id,
            timestamp=event.timestamp,
            attachments=[],
            metadata={
                "channel_type": event.channel.type.value,
                "event_id": event.event_id,
                "reply_to": event.reply_to
            }
        )

    def _create_response_message(self, content: str, reply_to_message: Message) -> Message:
        """Create a response message from the agent"""
        author = Author(
            id=self.agent_id,
            name=self.name,
            discord_id=f"bot_{self.agent_id}"
        )
        
        return Message(
            content=content,
            type=MessageType.TEXT,
            author=author,
            conversation_id=reply_to_message.conversation_id,
            timestamp=datetime.utcnow(),
            metadata={
                "reply_to_message_id": reply_to_message.id
            }
        )
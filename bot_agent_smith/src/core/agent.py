from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime, UTC
from langgraph.graph import StateGraph, END

from src.interfaces.types import CommunicationEvent, ChannelAdapter
from src.core.types import Message, Author, MessageType
from src.orchestration.services.registry import ServiceRegistry
from src.memory.chroma import MessageRepository, UserRepository
from src.core.logger import logger
from src.orchestration.workflows.workflow import ConversationWorkflow
from src.orchestration.workflows.state import WorkflowState
from src.orchestration.workflows.qualified_workflow import create_qualified_workflow
import asyncio
from collections import deque


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
        """Initialize services and LangGraph workflows"""
        # Import required services
        from src.llm import create_llm_client, get_default_model, get_available_models
        from src.llm.service import LLMService
        from src.skills.reasoning.qualifier import QualifierService
        from src.skills.reasoning.keyword_extraction import KeywordExtractionService
        from src.skills.web_search.article_search import ArticleSearchService
        from src.skills.context.service import ContextService
        import os

        # Get available model families
        available_models = get_available_models()
        default_model = get_default_model()
        
        logger.info(f"Initializing with available models: {available_models}")
        logger.info(f"Default model: {default_model}")
        
        # Initialize LLM clients and register services for each model family
        for model_family in available_models:
            # Initialize LLM client
            try:
                llm_client = create_llm_client(model_family)
                
                # Register LLM service for this model family
                llm_service = LLMService(client=llm_client, model_family=model_family)
                service_name = f"llm_{model_family.lower()}"
                
                self.service_registry.register(
                    name=service_name,
                    service=llm_service,
                    description=f"Handles LLM interactions using {model_family}",
                    version="1.0.0"
                )
                
                logger.info(f"Registered LLM service for model family: {model_family}")
                
            except ValueError as e:
                # Skip if model can't be initialized
                logger.warning(f"Could not initialize LLM client for {model_family}: {str(e)}")
        
        # Also register a default LLM service for backward compatibility
        try:
            default_llm_service = self.service_registry.get_service(f"llm_{default_model.lower()}")
            self.service_registry.register(
                name="llm",
                service=default_llm_service,
                description=f"Default LLM service (using {default_model})",
                version="1.0.0"
            )
        except KeyError:
            # If default model wasn't registered, use the first available
            for model_family in available_models:
                try:
                    fallback_service = self.service_registry.get_service(f"llm_{model_family.lower()}")
                    self.service_registry.register(
                        name="llm",
                        service=fallback_service,
                        description=f"Default LLM service (using {model_family})",
                        version="1.0.0"
                    )
                    logger.info(f"Using {model_family} as fallback default LLM")
                    break
                except KeyError:
                    continue
        
        # Get the default LLM client for other services
        default_llm_client = create_llm_client(default_model)
        
        # Register context service 
        context_service = ContextService(
            message_repository=self.message_repository,
            user_repository=self.user_repository
        )
        self.service_registry.register(
            name="context",
            service=context_service,
            description="Manages conversation context",
            version="1.0.0"
        )
        
        # Register qualifier service
        qualifier_service = QualifierService(
            ollama_client=default_llm_client,  # Parameter name kept for backward compatibility
            message_repository=self.message_repository
        )
        self.service_registry.register(
            name="qualifier",
            service=qualifier_service,
            description="Determines if a message needs counter-arguments",
            version="1.0.0"
        )
        
        # Register keyword extraction service
        keyword_extraction_service = KeywordExtractionService(
            ollama_client=default_llm_client  # Parameter name kept for backward compatibility
        )
        self.service_registry.register(
            name="keyword_extraction",
            service=keyword_extraction_service,
            description="Extracts keywords from messages for article searches",
            version="1.0.0"
        )

        # Register article search service
        article_search_service = ArticleSearchService(
            ollama_client=default_llm_client  # Parameter name kept for backward compatibility
        )
        self.service_registry.register(
            name="article_search",
            service=article_search_service,
            description="Searches for articles based on keywords",
            version="1.0.0"
        )

        # Initialize qualified workflow with registered services
        self.workflow = create_qualified_workflow(self.service_registry)

        logger.info(f"Initialized LangGraph workflow and services with default model family: {default_model}")
    
    def register_adapter(self, channel_type: str, adapter: ChannelAdapter):
        """Register a new channel adapter"""
        self.adapters[channel_type] = adapter
        logger.info(f"Registered adapter for channel type: {channel_type}")
        
    async def start(self):
        """Start all registered adapters and the message queue"""
        for channel_type, adapter in self.adapters.items():
            logger.info(f"Starting adapter for channel: {channel_type}")
            await adapter.initialize()
            await adapter.start()
            
    async def stop(self):
        """Stop all registered adapters and the message queue processor"""
                
        # Stop adapters
        for channel_type, adapter in self.adapters.items():
            logger.info(f"Stopping adapter for channel: {channel_type}")
            await adapter.stop()

    processed_events = set()  # Track already processed event IDs

    async def handle_event(self, event: CommunicationEvent) -> Optional[str]:
        """Process a communication event using LangGraph workflow"""
        # Simple duplication prevention
        if event.event_id in self.processed_events:
            logger.info(f"Event {event.event_id} already processed, skipping")
            return None
            
        self.processed_events.add(event.event_id)
        
        logger.info(f"========== HANDLING EVENT ==========")
        logger.info(f"Channel: {event.channel.type.value}")
        logger.info(f"Content: {event.content[:100]}...")
        
        # Convert event to message
        message = self._event_to_message(event)
        logger.info(f"Converted to message ID: {message.id}")
        
        # Store message in repository
        self.message_repository.add(message)
        logger.info("Message stored in repository")
        
        # Qualify the message
        qualifier_service = self.service_registry.get_service("qualifier")
        needs_counter_arguments = qualifier_service.execute(message=message)
        logger.info(f"Qualification result: {needs_counter_arguments}")
        
        # If counter-arguments needed, send acknowledgment first
        if needs_counter_arguments:
            channel_adapter = self.adapters.get(event.channel.type.value)
            if channel_adapter:
                ack_message = "🔄 I'm looking for different perspectives on this topic. I'll share what I find shortly..."
                
                await channel_adapter.send_message(
                    channel_id=event.channel.channel_id,
                    content=ack_message,
                    reply_to=event.event_id
                )
                
                # Store acknowledgment
                ack = self._create_response_message(
                    content=ack_message,
                    reply_to_message=message
                )
                self.message_repository.add(ack)
        
        # Set up workflow input with qualification result already set
        workflow_input = {
            "message": message,
            "context": {},
            "response": "",
            "needs_counter_arguments": needs_counter_arguments,
            "keywords": [],
            "articles": [],
            "counter_arguments": [],
            "messages_to_send": [],
            "_skip_qualification": True  # Skip qualification in workflow
        }
        
        # Process through workflow
        result = self.workflow.invoke(workflow_input)
        
        # Send final response
        if result and result.get("response"):
            response = result["response"]
            logger.info(f"Final response: {response[:100]}...")
            
            # Store response in repository (still do this)
            response_message = self._create_response_message(
                content=response,
                reply_to_message=message
            )
            self.message_repository.add(response_message)
            
            # Just return the response, don't send it
            return response
        
        logger.info("========== EVENT HANDLING COMPLETE ==========")
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
            timestamp=datetime.now(UTC),
            metadata={
                "reply_to_message_id": reply_to_message.id
            }
        )

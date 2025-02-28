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
        # Initialize Ollama client and service
        from src.llm.ollama import create_ollama_client
        from src.llm.service import LLMService
        from src.skills.reasoning.qualifier import QualifierService
        from src.skills.reasoning.keyword_extraction import KeywordExtractionService
        from src.skills.web_search.article_search import ArticleSearchService
        # from src.skills.reasoning.counter_argument import CounterArgumentService
        import os

        # Initialize Ollama client and service
        ollama_client = create_ollama_client(
            base_url=os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
            model=os.getenv('OLLAMA_MODEL', 'qwen2.5')
        )
        
        # Register LLM service
        llm_service = LLMService(client=ollama_client)
        self.service_registry.register(
            name="llm",
            service=llm_service,
            description="Handles LLM interactions using Ollama",
            version="1.0.0"
        )
        
        # Register context service 
        from src.skills.context.service import ContextService
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
            ollama_client=ollama_client,
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
            ollama_client=ollama_client
        )
        self.service_registry.register(
            name="keyword_extraction",
            service=keyword_extraction_service,
            description="Extracts keywords from messages for article searches",
            version="1.0.0"
        )

        # Register article search service
        article_search_service = ArticleSearchService(
            ollama_client=ollama_client
        )
        self.service_registry.register(
            name="article_search",
            service=article_search_service,
            description="Searches for articles based on keywords",
            version="1.0.0"
        )

        # Initialize qualified workflow with registered services
        self.workflow = create_qualified_workflow(self.service_registry)
        
        logger.info("Initialized LangGraph workflow and services")
    
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
        """Process a communication event using LangGraph workflow"""
        logger.info(f"========== HANDLING EVENT ==========")
        logger.info(f"Channel: {event.channel.type.value}")
        logger.info(f"Content: {event.content[:100]}...")
        
        message = self._event_to_message(event)
        logger.info(f"Converted to message ID: {message.id}")
        
        self.message_repository.add(message)
        logger.info("Message stored in repository")
        
        # Prepare workflow input
        initial_state = {
            "message": message,
            "context": {},
            "response": "",
            "needs_counter_arguments": False
        }
        
        logger.info("Starting workflow execution...")
        result = self.workflow.invoke(initial_state)
        logger.info(f"Workflow execution completed with response: {bool(result.get('response'))}")
        
        if result and result.get("response"):
            response = result["response"]
            logger.info(f"Response: {response[:100]}...")
            
            response_message = self._create_response_message(
                content=response,
                reply_to_message=message
            )
            self.message_repository.add(response_message)
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
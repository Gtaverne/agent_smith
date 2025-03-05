# tests/test_workflows/test_basic.py

from src.orchestration.workflows.simple_workflow import create_workflow
from src.orchestration.services.registry import ServiceRegistry
from src.core.types import Message, Author, MessageType
from src.llm.ollama import create_ollama_client
from src.llm.service import LLMService
from agent_smith.bot_agent_smith.src.memory.chroma_db.chroma import ChromaClient, MessageRepository, UserRepository
from src.skills.context.service import ContextService
import os
from datetime import datetime, UTC
import uuid

def test_workflow_with_services():
    print("\nStarting workflow integration test...")
    
    # Initialize services
    print("\nInitializing services...")
    
    # Create ChromaDB client
    chroma = ChromaClient(
        host=os.getenv('CHROMA_HOST', 'localhost'),
        port=int(os.getenv('CHROMA_PORT', '8184'))
    )
    
    # Initialize repositories
    message_repo = MessageRepository(chroma)
    user_repo = UserRepository(chroma)
    
    # Create Ollama client
    ollama_client = create_ollama_client(
        base_url=os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
        model=os.getenv('OLLAMA_MODEL', 'qwen2.5')  # Make sure this model is pulled
    )
    
    # Initialize services
    service_registry = ServiceRegistry()
    
    # Register LLM service
    llm_service = LLMService(client=ollama_client)
    service_registry.register(
        name="llm",
        service=llm_service,
        description="LLM service using Ollama",
        version="1.0.0"
    )
    
    # Register context service
    context_service = ContextService(
        message_repository=message_repo,
        user_repository=user_repo
    )
    service_registry.register(
        name="context",
        service=context_service,
        description="Manages conversation context",
        version="1.0.0"
    )
    
    print("Services initialized")
    
    # Create workflow
    workflow = create_workflow(service_registry)
    print("\nWorkflow created")
    
    # Create test message
    test_message = Message(
        id=str(uuid.uuid4()),
        content="What is the capital of France?",
        type=MessageType.TEXT,
        author=Author(
            id="test_user",
            name="Test User",
            discord_id="test123"
        ),
        conversation_id="test_conv",
        timestamp=datetime.now(UTC)
    )
    
    # Create test input
    test_input = {
        "message": test_message,
        "context": {},
        "response": ""
    }
    
    print(f"\nSending message: {test_message.content}")
    
    # Run workflow
    result = workflow.invoke(test_input)
    
    # Print results
    print(f"\nWorkflow results:")
    print(f"Input: {test_message.content}")
    print(f"Response: {result['response']}")
    print(f"Context: {result['context']}")
    
    # Basic assertions
    assert "response" in result, "Response missing from result"
    assert result["response"], "Empty response received"
    assert "context" in result, "Context missing from result"
    
    print("\nAll tests passed successfully!")

if __name__ == "__main__":
    test_workflow_with_services()
# tests/test_skills/test_counterpoints/test_qualifier.py

from datetime import datetime, UTC
import uuid
from dotenv import load_dotenv
import os

from src.core.types import Message, Author, MessageType
from src.skills.reasoning.qualifier import QualifierService
from src.llm.ollama import create_ollama_client
from src.memory import create_vector_db_client, create_message_repository
from src.orchestration.services.registry import ServiceRegistry

def create_test_message(content: str, conversation_id: str = None) -> Message:
    """Helper to create test messages"""
    return Message(
        id=str(uuid.uuid4()),
        content=content,
        type=MessageType.TEXT,
        author=Author(
            id="test_user",
            name="Test User",
            discord_id="test123"
        ),
        conversation_id=conversation_id or str(uuid.uuid4()),
        timestamp=datetime.now(UTC)
    )

def test_qualifier_service():
    """Test the Bubble Buster qualifier service"""
    print("\nStarting Bubble Buster integration test...")
    
    # Load environment variables
    load_dotenv()
    
    # Initialize clients and service
    client = create_ollama_client(
        base_url=os.getenv('OLLAMA_HOST'),
        model=os.getenv('OLLAMA_MODEL')
    )
    
    vector_db_client = create_vector_db_client(
        db_type=os.getenv('VECTOR_DB_TYPE', 'chroma'),
        host=os.getenv('CHROMA_HOST', 'localhost'),
        port=int(os.getenv('CHROMA_PORT', '8184'))
    )
    message_repo = create_message_repository(vector_db_client)
    
    service = QualifierService(
        ollama_client=client,
        message_repository=message_repo
    )
    
    # Test standalone messages that should NOT get counter-arguments
    print("\nTesting simple standalone queries...")
    simple_queries = [
        "What time is it?",
        "How do I open VSCode?",
        "What's the weather like?",
        "Can you help me with Python syntax?",
        "What's your name?",
        "Hello",
        "Thanks"
    ]
    
    for content in simple_queries:
        message = create_test_message(content)
        result = service.execute(message=message)
        print(f"Message: '{content}' -> Need counter-arguments: {result}")
        assert result is False, f"Should not need counter-arguments for simple query: {content}"
    
    # Test messages with conversation context
    print("\nTesting messages with context...")
    
    # Example 1: Discussion about AI
    conv_id = str(uuid.uuid4())
    context_messages = [
        create_test_message("I've been reading about AI safety.", conv_id),
        create_test_message("What do you think about AI development?", conv_id),
        create_test_message("I believe AI will be entirely beneficial to society.", conv_id)
    ]
    
    # Add context messages to repository
    for msg in context_messages:
        message_repo.add(msg)
    
    # Test final message in context
    result = service.execute(context_messages[-1])
    print(f"\nAI discussion -> Need counter-arguments: {result}")
    assert result is True, "Should explore counter-arguments for AI discussion"
    
    # Example 2: Technical help conversation
    conv_id = str(uuid.uuid4())
    tech_messages = [
        create_test_message("I'm learning Python", conv_id),
        create_test_message("How do I write a for loop?", conv_id),
        create_test_message("Thanks for the help!", conv_id)
    ]
    
    # Add context messages to repository
    for msg in tech_messages:
        message_repo.add(msg)
    
    # Test final message in context
    result = service.execute(tech_messages[-1])
    print(f"\nTechnical help discussion -> Need counter-arguments: {result}")
    assert result is False, "Should not need counter-arguments for technical help"
    
    # Example 3: Vague statement becoming clearer with context
    conv_id = str(uuid.uuid4())
    context_messages = [
        create_test_message("Let's talk about education reform.", conv_id),
        create_test_message("The current system needs changes.", conv_id),
        create_test_message("Standardized testing is the best way to measure student success.", conv_id)
    ]
    
    # Add context messages to repository
    for msg in context_messages:
        message_repo.add(msg)
    
    # Test final message in context
    result = service.execute(context_messages[-1])
    print(f"\nEducation discussion -> Need counter-arguments: {result}")
    assert result is True, "Should explore counter-arguments for education discussion"

def test_qualifier_in_registry():
    """Test qualifier works properly when registered as a service"""
    print("\nTesting Bubble Buster in service registry...")
    
    # Initialize components
    client = create_ollama_client(
        base_url=os.getenv('OLLAMA_HOST'),
        model=os.getenv('OLLAMA_MODEL')
    )
    
    vector_db_client = create_vector_db_client(
        db_type=os.getenv('VECTOR_DB_TYPE', 'chroma'),
        host=os.getenv('CHROMA_HOST', 'localhost'),
        port=int(os.getenv('CHROMA_PORT', '8184'))
    )
    message_repo = create_message_repository(vector_db_client)
    
    service = QualifierService(
        ollama_client=client,
        message_repository=message_repo
    )
    
    registry = ServiceRegistry()
    registry.register(
        name="qualifier",
        service=service,
        description="Bubble Buster service that identifies opportunities to explore different viewpoints",
        version="1.0.0"
    )
    
    # Create a test conversation
    conv_id = str(uuid.uuid4())
    messages = [
        create_test_message("Machine learning is transforming every industry", conv_id),
        create_test_message("Especially in healthcare", conv_id),
        create_test_message("ML models are always accurate and unbiased", conv_id)
    ]
    
    # Add messages to repository
    for msg in messages:
        message_repo.add(msg)
    
    # Test through registry
    qualifier_service = registry.get_service("qualifier")
    result = qualifier_service.execute(messages[-1])
    print(f"\nML discussion through registry -> Need counter-arguments: {result}")
    
    assert result is True, "Should identify opportunity to challenge assumptions through registry"

if __name__ == "__main__":
    test_qualifier_service()
    test_qualifier_in_registry()
    print("\nAll tests passed successfully!")
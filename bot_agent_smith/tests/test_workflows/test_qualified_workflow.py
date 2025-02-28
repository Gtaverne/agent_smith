# tests/test_workflows/test_qualified_counter_workflow.py
from src.orchestration.workflows.qualified_workflow import create_qualified_workflow
from src.orchestration.services.registry import ServiceRegistry
from src.core.types import Message, Author, MessageType
from src.llm.ollama import create_ollama_client
from src.llm.service import LLMService
from src.memory.chroma import ChromaClient, MessageRepository, UserRepository
from src.skills.context.service import ContextService
from src.skills.reasoning.qualifier import QualifierService
from src.skills.reasoning.keyword_extraction import KeywordExtractionService
from src.skills.web_search.article_search import ArticleSearchService

import os
from datetime import datetime, UTC
import uuid
import re

def test_counter_argument_workflow():
    print("\nStarting counter-argument workflow test...")
    
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
    
    # Initialize service registry
    service_registry = ServiceRegistry()
    
    # Register services
    llm_service = LLMService(client=ollama_client)
    service_registry.register(
        name="llm",
        service=llm_service,
        description="LLM service using Ollama",
        version="1.0.0"
    )
    
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
    
    qualifier_service = QualifierService(
        ollama_client=ollama_client,
        message_repository=message_repo
    )
    service_registry.register(
        name="qualifier",
        service=qualifier_service,
        description="Determines if a message needs counter-arguments",
        version="1.0.0"
    )
    
    keyword_extraction_service = KeywordExtractionService(
        ollama_client=ollama_client
    )
    service_registry.register(
        name="keyword_extraction",
        service=keyword_extraction_service,
        description="Extracts keywords from messages",
        version="1.0.0"
    )
    
    article_search_service = ArticleSearchService(
        ollama_client=ollama_client
    )
    service_registry.register(
        name="article_search",
        service=article_search_service,
        description="Searches for articles based on keywords",
        version="1.0.0"
    )
    
    print("Services initialized")
    
    # Create workflow
    workflow = create_qualified_workflow(service_registry)
    print("\nWorkflow created")
    
    # Test cases
    test_cases = [
        {
            "description": "Statement likely to need counter-arguments",
            "content": "I believe artificial intelligence will inevitably lead to human job loss across all sectors.",
            "expect_counter_arguments": True
        },
        {
            "description": "Statement likely to need counter-arguments about a controversial topic",
            "content": "Nuclear energy is too dangerous and should be banned worldwide.",
            "expect_counter_arguments": True
        },
        {
            "description": "Simple factual question (should NOT need counter-arguments)",
            "content": "What is the capital of France?",
            "expect_counter_arguments": False
        }
    ]
    
    # Run workflow for each test case
    for i, test_case in enumerate(test_cases):
        print(f"\n\n===== Test Case {i+1}: {test_case['description']} =====")
        
        # Create test message
        test_message = Message(
            id=str(uuid.uuid4()),
            content=test_case['content'],
            type=MessageType.TEXT,
            author=Author(
                id="test_user",
                name="Test User",
                discord_id="test123"
            ),
            conversation_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC)
        )
        
        # Add message to repository for context
        message_repo.add(test_message)
        
        # Create workflow input
        workflow_input = {
            "message": test_message,
            "context": {},
            "response": "",
            "needs_counter_arguments": False,
            "keywords": [],
            "articles": [],
            "counter_arguments": []
        }
        
        print(f"\nMessage: {test_message.content}")
        
        # Run workflow
        result = workflow.invoke(workflow_input)
        
        # Print results
        print(f"\nWorkflow results:")
        print(f"Needs counter-arguments: {result.get('needs_counter_arguments', False)}")
        
        if result.get('needs_counter_arguments', False):
            print(f"Keywords extracted: {result.get('keywords', [])}")
            print(f"Articles found: {len(result.get('articles', []))}")
            print(f"Counter-arguments: {len(result.get('counter_arguments', []))}")
            
            # Check for notification in response
            notification_pattern = r"🔄.*different perspectives"
            has_notification = bool(re.search(notification_pattern, result.get('response', '')))
            print(f"Has notification: {has_notification}")
            
            assert has_notification, "Response should include notification about counter-arguments"
        
        # Print first part of response
        response_preview = result.get('response', '')[:150] + "..." if result.get('response') else "No response"
        print(f"\nResponse preview: {response_preview}")
        
        # Assertions
        assert "response" in result, "Response missing from result"
        assert result["response"], "Empty response received"
        assert "context" in result, "Context missing from result"
        assert "needs_counter_arguments" in result, "Qualification result missing"
        
        # Check if counter-argument detection matches expectations
        assert result.get('needs_counter_arguments') == test_case['expect_counter_arguments'], \
            f"Expected needs_counter_arguments={test_case['expect_counter_arguments']}, " \
            f"got {result.get('needs_counter_arguments')}"
        
        # If counter-arguments expected, check that workflow produced them
        if test_case['expect_counter_arguments']:
            assert "keywords" in result, "Keywords missing from result"
            assert len(result["keywords"]) > 0, "No keywords extracted"
            assert "articles" in result, "Articles missing from result"
            assert len(result["articles"]) > 0, "No articles found"
            
            # Depending on article content, counter-arguments might not be found
            # so we don't assert they must exist
    
    print("\nAll workflow tests passed!")

if __name__ == "__main__":
    test_counter_argument_workflow()
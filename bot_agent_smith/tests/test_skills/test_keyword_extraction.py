import os
from dotenv import load_dotenv

from src.core.types import Message, Author, MessageType
from src.skills.reasoning.keyword_extraction import KeywordExtractionService
from src.llm.ollama import create_ollama_client

def test_keyword_extraction_service():
    """Test the keyword extraction service"""
    print("\nStarting keyword extraction service test...")
    
    # Load environment variables
    load_dotenv()
    
    # Initialize Ollama client
    client = create_ollama_client(
        base_url=os.getenv('OLLAMA_HOST'),
        model=os.getenv('OLLAMA_MODEL')
    )
    
    # Initialize service
    service = KeywordExtractionService(
        ollama_client=client
    )
    
    # Test messages
    test_messages = [
        "I believe artificial intelligence will inevitably lead to human job loss across all sectors.",
        "Climate change regulations are harming economic growth and innovation.",
        "Nuclear energy is the safest and most environmentally friendly form of power generation.",
        "The rise of social media has had a negative impact on mental health and social cohesion."
    ]
    
    # Test the service with each message
    for content in test_messages:
        print(f"\nTesting message: {content}")
        
        keywords = service.execute(message_content=content)
        
        print(f"Extracted keywords: {keywords}")
        
        # Basic assertions
        assert isinstance(keywords, list), "Result should be a list"
        assert len(keywords) == 3, f"Expected 3 keywords, got {len(keywords)}"
        assert all(isinstance(k, str) for k in keywords), "All keywords should be strings"
        assert all(k.strip() for k in keywords), "No empty keywords allowed"
        
    print("\nAll keyword extraction tests passed!")

if __name__ == "__main__":
    test_keyword_extraction_service()
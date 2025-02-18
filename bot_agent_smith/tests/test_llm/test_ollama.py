from src.llm.ollama import create_ollama_client
from src.llm.ollama.models import OllamaMessage
from dotenv import load_dotenv
import os

def test_ollama_integration():
    print("\nStarting Ollama integration test...")
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    base_url = os.getenv('OLLAMA_HOST')
    model = os.getenv('OLLAMA_MODEL')
    
    # Initialize client
    client = create_ollama_client(base_url=base_url, model=model)
    
    # Create a test message
    messages = [
        OllamaMessage(role="system", content="You are a helpful AI assistant."),
        OllamaMessage(role="user", content="What is the capital of France?")
    ]
    
    print(f"\nSending messages to {model} at {base_url}...")
    
    # Send message and get response
    response = client.send_message(messages)
    
    print(f"\nReceived response:")
    print(f"Model: {response.model}")
    print(f"Created at: {response.created_at}")
    print(f"Response: {response.response}")
    print(f"Done: {response.done}")
    print(f"Context length: {len(response.context) if response.context else 'No context'}")
    
    # Basic assertions
    assert response.model == model
    assert response.response, "Response should not be empty"
    assert response.done, "Response should be marked as done"
    
    print("\nAll tests passed successfully!")

if __name__ == "__main__":
    test_ollama_integration()
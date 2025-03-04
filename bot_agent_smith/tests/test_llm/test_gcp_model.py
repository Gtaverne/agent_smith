from src.llm.gcp_models import create_gcp_client
from src.llm.gcp_models.models import GCPMessage
from dotenv import load_dotenv
import os

def test_gcp_integration():
    print("\nStarting GCP integration test...")
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
        
    model = os.getenv('GCP_MODEL', 'gemini-1.0-pro')
    
    print(f"\nUsing model: {model}")
    
    # Initialize client
    client = create_gcp_client(api_key=api_key, model=model)
    
    # Create a test message
    messages = [
        GCPMessage(role="system", content="You are a helpful AI assistant."),
        GCPMessage(role="user", content="What is the capital of France?")
    ]
    
    print(f"\nSending messages to {model}...")
    
    # Send message and get response
    response = client.send_message(messages)
    
    print(f"\nReceived response:")
    print(f"Model: {response.model}")
    print(f"Created at: {response.created_at}")
    print(f"Response: {response.response}")
    print(f"Done: {response.done}")
    
    # Basic assertions
    assert response.model == model
    assert response.response, "Response should not be empty"
    assert response.done, "Response should be marked as done"
    
    print("\nAll tests passed successfully!")

if __name__ == "__main__":
    test_gcp_integration()
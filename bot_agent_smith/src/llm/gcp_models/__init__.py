from .client import GCPClient
from .models import GCPMessage, GCPResponse

def create_gcp_client(api_key: str, model: str) -> GCPClient:
    """
    Create and return a configured GCP client.
    
    Args:
        api_key: Google API key for authentication
        model: GCP model name to use (e.g., 'gemini-1.0-pro', 'gemini-1.0-pro-vision')
        
    Returns:
        Configured GCPClient instance
    """
    return GCPClient(api_key=api_key, model=model)
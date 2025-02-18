from .client import OllamaClient
from .models import OllamaMessage, OllamaResponse

def create_ollama_client(base_url: str, model: str) -> OllamaClient:
    return OllamaClient(base_url=base_url, model=model)
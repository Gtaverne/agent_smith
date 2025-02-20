from urllib.parse import urljoin
import httpx
from typing import List

from .models import OllamaMessage, OllamaResponse

class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
        self.timeout = httpx.Timeout(timeout=120.0)
        
    def _get_completion_url(self) -> str:
        return urljoin(self.base_url, "/api/generate")
        
    def send_message(self, messages: List[OllamaMessage]) -> OllamaResponse:
        url = self._get_completion_url()
        
        # Format payload for Ollama
        payload = {
            "model": self.model,
            "prompt": "\n".join(msg.content for msg in messages),
            "stream": False
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return OllamaResponse(
                model=data["model"],
                created_at=data.get("created_at", ""),
                response=data["response"],
                done=True,
                context=data.get("context")
            )
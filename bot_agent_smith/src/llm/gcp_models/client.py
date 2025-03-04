import google.generativeai as genai
from typing import List, Dict, Any
from datetime import datetime, UTC

from .models import GCPMessage, GCPResponse
from src.core.logger import logger

class GCPClient:
    """Client for interacting with Google GCP API."""
    
    def __init__(self, api_key: str, model: str):
        """
        Initialize the GCP client.
        
        Args:
            api_key: Google API key for authentication
            model: GCP model name to use (e.g., 'gemini-1.0-pro', 'gemini-1.0-pro-vision')
        """
        self.model = model
        self.api_key = api_key
        
        # Configure the GCP API
        genai.configure(api_key=api_key)
        
        # Initialize the model
        self.model_instance = genai.GenerativeModel(model_name=model)
        
    def send_message(self, messages: List[GCPMessage]) -> GCPResponse:
        """
        Send messages to GCP and get a response.
        
        Args:
            messages: List of GCPMessage objects
            
        Returns:
            GCPResponse object containing the model's response
        """
        logger.info(f"Sending request to GCP model: {self.model}")
        
        # Convert messages to GCP format
        gcp_messages = []
        
        # Handle system message if present (GCP handles system prompts differently)
        system_content = None
        history = []
        
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                history.append({"role": msg.role, "parts": [msg.content]})
        
        # If there's a system message, use it to configure the model
        if system_content:
            # GCP doesn't have direct system message support, so we need to get creative
            # Option 1: Prepend it to the first user message
            if history and history[0]["role"] == "user":
                history[0]["parts"][0] = f"{system_content}\n\n{history[0]['parts'][0]}"
            # Option 2: If first message isn't user, add a user message with system content
            else:
                history.insert(0, {"role": "user", "parts": [system_content]})
        
        # Create a chat session
        chat = self.model_instance.start_chat(history=history if len(history) > 1 else None)
        
        # Get response
        if not history or len(history) <= 1:
            # For the first message or if there's only one message after handling system
            content = history[0]["parts"][0] if history else ""
            response = self.model_instance.generate_content(content)
        else:
            # For continuing a conversation
            last_msg = history[-1]["parts"][0] if history[-1]["role"] == "user" else ""
            response = chat.send_message(last_msg)
        
        # Extract response text
        response_text = response.text
        
        # Create and return GCPResponse
        return GCPResponse(
            model=self.model,
            created_at=datetime.now(UTC).isoformat(),
            response=response_text,
            done=True,
            metadata={"prompt_feedback": getattr(response, "prompt_feedback", None)}
        )
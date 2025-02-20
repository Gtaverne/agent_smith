from dataclasses import dataclass
from typing import List, Dict, Any

from .ollama import OllamaClient, OllamaMessage
from src.orchestration.services.registry import ServiceProtocol

from src.core.logger import logger

@dataclass
class LLMService(ServiceProtocol):
    """Service for handling LLM interactions"""
    client: OllamaClient  # We use this name in constructor

    def execute(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """
        Process messages through Ollama LLM
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            
        Returns:
            str: LLM response text
        """
        logger.info("========== LLM SERVICE EXECUTION ==========")
        logger.info(f"Processing {len(messages)} messages through LLM")
        
        # Log the messages being sent to LLM
        for i, msg in enumerate(messages):
            logger.info(f"Message {i + 1}:")
            logger.info(f"Role: {msg['role']}")
            logger.info(f"Content: {msg['content'][:100]}...")
        
        # Convert dictionary messages to OllamaMessage objects
        ollama_messages = [
            OllamaMessage(
                role=msg["role"],
                content=msg["content"]
            )
            for msg in messages
        ]
        
        logger.info("Sending request to Ollama...")
        
        # Send to Ollama and get response
        response = self.client.send_message(ollama_messages)  # Changed from ollama_client to client
        
        logger.info("Received response from Ollama")
        logger.info(f"Response content: {response.response[:100]}...")
        logger.info("========== LLM SERVICE COMPLETE ==========")
        
        return response.response
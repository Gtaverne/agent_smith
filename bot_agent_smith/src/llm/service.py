from dataclasses import dataclass
from typing import List, Dict, Any, Protocol, Union, Optional

from src.orchestration.services.registry import ServiceProtocol
from src.core.logger import logger


@dataclass
class LLMService(ServiceProtocol):
    """Service for handling LLM interactions"""
    client: Any  # Accept any client, we'll check type at runtime
    model_family: str = None  # The model family this service is associated with

    def execute(self, messages: List[Dict[str, str]], model_family: Optional[str] = None, **kwargs: Any) -> str:
        """
        Process messages through LLM
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model_family: Override model family to use (if None, uses the service's model)
            
        Returns:
            str: LLM response text
        """
        # Use either the provided model family or the service's model family
        used_model_family = model_family or self.model_family
        
        logger.info("========== LLM SERVICE EXECUTION ==========")
        logger.info(f"Processing {len(messages)} messages through LLM")
        logger.info(f"Using {type(self.client).__module__}.{type(self.client).__name__}")
        logger.info(f"Model family: {used_model_family}")
        
        # Log the messages being sent to LLM
        for i, msg in enumerate(messages):
            logger.info(f"Message {i + 1}:")
            logger.info(f"Role: {msg['role']}")
            logger.info(f"Content: {msg['content'][:100]}...")
        
        # Determine client type based on module name
        client_module = type(self.client).__module__
        
        # Convert messages based on client type
        if "ollama" in client_module:
            # Import here to avoid circular imports
            from src.llm.ollama import OllamaMessage
            
            # Convert to OllamaMessage objects
            converted_messages = [
                OllamaMessage(
                    role=msg["role"],
                    content=msg["content"]
                )
                for msg in messages
            ]
            
        elif "gcp_models" in client_module:
            # Import here to avoid circular imports
            from src.llm.gcp_models import GCPMessage
            
            # Convert to GCPMessage objects
            converted_messages = [
                GCPMessage(
                    role=msg["role"],
                    content=msg["content"]
                )
                for msg in messages
            ]
            
        else:
            # Unknown client type, but we'll try a generic approach
            logger.warning(f"Unknown LLM client type: {client_module}")
            logger.warning("Trying generic message format...")
            
            # Assume the client accepts dictionaries
            converted_messages = messages
        
        logger.info(f"Sending request to LLM client...")
        
        # Send to LLM and get response
        response = self.client.send_message(converted_messages)
        
        logger.info("Received response from LLM")
        logger.info(f"Response content: {response.response[:100]}...")
        logger.info("========== LLM SERVICE COMPLETE ==========")
        
        return response.response
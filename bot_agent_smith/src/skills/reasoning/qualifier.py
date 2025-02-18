from dataclasses import dataclass
from typing import Optional

from src.core.types import Message
from src.llm.ollama import OllamaClient, OllamaMessage
from src.orchestration.services.registry import ServiceProtocol

@dataclass
class QualifierService(ServiceProtocol):
    ollama_client: OllamaClient

    def execute(self, message: Message) -> bool:
        """
        Determine if a message needs counter-arguments.
        
        Args:
            message: The message to analyze
            
        Returns:
            bool: True if the message needs counter-arguments
        """
        # Create messages for Ollama
        messages = [
            OllamaMessage(
                role="system",
                content="""You are a message qualifier that determines if a message needs counter-arguments.
                
                A message needs counter-arguments if:
                1. It expresses a clear opinion or stance on a topic
                2. The user explicitly asks for different viewpoints
                3. The message is argumentative or debatable
                4. The message contains claims that could be challenged
                
                Return ONLY true or false.
                """
            ),
            OllamaMessage(
                role="user",
                content=f"Message: {message.content}\n\nDoes this message need counter-arguments? Answer with only true or false."
            )
        ]

        # Get response from Ollama
        response = self.ollama_client.send_message(messages)
        
        # Parse response - looking for true/false
        return response.response.lower().strip() == "true"
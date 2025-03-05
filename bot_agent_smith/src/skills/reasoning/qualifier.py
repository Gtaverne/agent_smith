from dataclasses import dataclass
from typing import Optional, List, Any
from datetime import datetime, UTC

from src.core.types import Message
from src.core.logger import logger
from src.memory.chroma_db.chroma import MessageRepository
from src.orchestration.services.registry import ServiceProtocol

@dataclass
class QualifierService(ServiceProtocol):
    """Service that determines if a message needs counter-arguments"""
    ollama_client: Any  # Renamed internally but kept for backward compatibility
    message_repository: MessageRepository
    window_size: int = 3
    model_family: Optional[str] = None

    def __post_init__(self):
        if self.model_family is None:
            from src.llm import get_default_model
            self.model_family = get_default_model()

    def execute(self, message: Message, model_family: Optional[str] = None) -> bool:
        """
        Determine if a message needs counter-arguments.
        Consider recent conversation context.
        
        Args:
            message: The message to analyze
            model_family: Optional model family to use (overrides the default)
            
        Returns:
            bool: True if the message needs counter-arguments
        """
        # Use specified model_family or the default
        client = self.ollama_client
        used_model_family = model_family or self.model_family
        
        logger.info(f"QualifierService using model family: {used_model_family}")
        logger.info(f"QualifierService analyzing: {message.content}")

        # Get recent messages for context
        conversation_messages = self.message_repository.get_by_conversation(
            message.conversation_id
        )
        # Sort by timestamp and get last n messages
        conversation_messages.sort(key=lambda m: m.timestamp)
        context_messages = conversation_messages[-self.window_size:]
        
        # Format context for prompt
        context_str = "\n".join([
            f"{msg.author.name}: {msg.content}" 
            for msg in context_messages
        ])

        # Create system and user prompts
        system_prompt = """You are the Bubble Buster, analyzing conversations for opportunities to explore different viewpoints.

        Consider these criteria before deciding:
        1. Specificity: Does the message or conversation context contain concrete claims or topics?
        2. Substance: Is there enough meaningful content to find opposing views?
        3. Clarity: Are the claims or topics clear enough without needing clarification?

        Return false for:
        - Simple factual queries or greetings
        - Vague statements without context ("it's the best")
        - Personal preferences without broader implications
        - Technical how-to questions
        - Basic identity questions
        - Messages lacking specific claims or topics

        Return true only when:
        1. There are clear, specific topics or claims to explore
        2. The conversation provides enough context to understand the topic
        3. The content is substantial enough to meaningfully explore different viewpoints

        Return ONLY true or false.
        """
        
        user_prompt = f"""Recent conversation:
        {context_str}
        
        Current message: {message.content}

        Should we explore counter-arguments or alternative perspectives for this conversation? Answer with only true or false."""
        
        # Determine client type based on module name
        client_module = type(client).__module__
        
        # Create messages for LLM based on client type
        if "ollama" in client_module:
            # Import here to avoid circular imports
            from src.llm.ollama import OllamaMessage
            messages = [
                OllamaMessage(role="system", content=system_prompt),
                OllamaMessage(role="user", content=user_prompt)
            ]
        elif "gcp_models" in client_module:
            # Import here to avoid circular imports
            from src.llm.gcp_models import GCPMessage
            messages = [
                GCPMessage(role="system", content=system_prompt),
                GCPMessage(role="user", content=user_prompt)
            ]
        else:
            # Generic approach for unknown client types
            logger.warning(f"Unknown LLM client type in QualifierService: {client_module}")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

        # Get response from the LLM client
        response = client.send_message(messages)
        logger.info(f"QualifierService received response: {response.response}")
        
        # Parse the response, handling different formats
        response_text = response.response.lower().strip()
        
        # Look for a true/false value
        if "true" in response_text and "false" not in response_text:
            return True
        elif "false" in response_text and "true" not in response_text:
            return False
        else:
            # If both or neither appears, check the beginning of the response
            if response_text.startswith("true"):
                return True
            elif response_text.startswith("false"):
                return False
            else:
                # Default to false if we can't determine
                logger.warning(f"Couldn't clearly determine true/false from response: {response_text}")
                return False
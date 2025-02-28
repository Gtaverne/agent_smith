# src/skills/reasoning/qualifier.py

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, UTC

from src.core.types import Message
from src.core.logger import logger
from src.memory.chroma import MessageRepository
from src.llm.ollama import OllamaClient, OllamaMessage
from src.orchestration.services.registry import ServiceProtocol

@dataclass
class QualifierService(ServiceProtocol):
    """Service that determines if a message needs counter-arguments"""
    ollama_client: OllamaClient
    message_repository: MessageRepository
    window_size: int = 3

    def execute(self, message: Message) -> bool:
        """
        Determine if a message needs counter-arguments.
        Consider recent conversation context.
        
        Args:
            message: The message to analyze
            
        Returns:
            bool: True if the message needs counter-arguments
        """
        logger.info(f"QualifierService: {message.content}")

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

        # Create messages for Ollama
        messages = [
            OllamaMessage(
                role="system",
                content="""You are the Bubble Buster, analyzing conversations for opportunities to explore different viewpoints.

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
            ),
            OllamaMessage(
                role="user",
                content=f"""Recent conversation:
                {context_str}
                
                Current message: {message.content}

                Should we explore counter-arguments or alternative perspectives for this conversation? Answer with only true or false."""
            )
        ]

        # Get response from Ollama
        response = self.ollama_client.send_message(messages)
        logger.info(f"QualifierService received response: {response.response}")
        
        return response.response.lower().strip() == "true"
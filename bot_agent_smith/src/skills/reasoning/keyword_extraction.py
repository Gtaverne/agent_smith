from dataclasses import dataclass
from typing import List, Dict, Any

from src.core.logger import logger
from src.orchestration.services.registry import ServiceProtocol

@dataclass
class KeywordExtractionService(ServiceProtocol):
    """Service that extracts keywords from a message for searching articles"""
    ollama_client: Any  # Parameter name kept for backward compatibility
    
    def execute(self, message_content: str, **kwargs) -> List[str]:
        """
        Extract keywords from a message content
        
        Args:
            message_content: The message content to analyze
            
        Returns:
            List[str]: List of extracted keywords (typically 3)
        """
        logger.info(f"Extracting keywords from: {message_content[:100]}...")
        
        # System and user prompts
        system_prompt = """You are a keyword extraction system that identifies the most relevant 
        search terms from a user's message or conversation.
        
        Extract exactly 3 keywords or short phrases that:
        1. Capture the main topic being discussed
        2. Are suitable for searching for articles on this topic
        3. Would help find diverse perspectives on the topic
        
        Format your response as a JSON list of exactly 3 strings, nothing else:
        ["keyword1", "keyword2", "keyword3"]
        """
        
        user_prompt = f"""Extract the 3 most important keywords from this message:
        
        "{message_content}"
        
        Remember to respond with only a JSON array of 3 keywords.
        """
        
        # Determine client type based on module name
        client_module = type(self.ollama_client).__module__
        
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
            from src.llm.gcp_models.models import GCPMessage
            messages = [
                GCPMessage(role="system", content=system_prompt),
                GCPMessage(role="user", content=user_prompt)
            ]
        else:
            # Generic approach for unknown client types
            logger.warning(f"Unknown LLM client type in KeywordExtractionService: {client_module}")
            # Create messages as properly formatted objects for this client type,
            # not just dictionaries
            from src.llm.service import LLMService
            if isinstance(self.ollama_client, LLMService):
                # If we have an LLMService, use dicts as it expects
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            else:
                # Default case, let's try the GCPMessage format
                from src.llm.gcp_models.models import GCPMessage
                messages = [
                    GCPMessage(role="system", content=system_prompt),
                    GCPMessage(role="user", content=user_prompt)
                ]
        
        # Get response from the LLM client
        response = self.ollama_client.send_message(messages)
        logger.info(f"Keyword extractor received response: {response.response}")
        
        # Parse the response to extract keywords
        try:
            # The response should be a JSON array, but let's handle common formatting issues
            import json
            import re
            
            # Try to extract just the JSON array using regex in case there's extra text
            json_match = re.search(r'\[.*?\]', response.response, re.DOTALL)
            if json_match:
                keywords_json = json_match.group(0)
                keywords = json.loads(keywords_json)
            else:
                # Fallback: try to parse the whole response
                keywords = json.loads(response.response)
                
            # Ensure we have exactly 3 keywords
            if not isinstance(keywords, list):
                logger.warning("Response is not a list, using default keywords")
                return ["artificial intelligence", "ethics", "technology"]
                
            # Limit to 3 keywords
            keywords = keywords[:3]
            
            # If we have fewer than 3, add defaults
            while len(keywords) < 3:
                keywords.append("technology")
                
            logger.info(f"Extracted keywords: {keywords}")
            return keywords
            
        except Exception as e:
            logger.error(f"Error parsing keywords: {e}")
            # Return default keywords in case of parsing error
            return ["artificial intelligence", "ethics", "technology"]
# src/skills/web_search/article_search.py
from dataclasses import dataclass
from typing import List, Dict, Any

from src.core.logger import logger
from src.llm.ollama import OllamaClient, OllamaMessage
from src.orchestration.services.registry import ServiceProtocol

@dataclass
class ArticleSearchService(ServiceProtocol):
    """Service that searches for articles based on keywords"""
    ollama_client: OllamaClient
    
    def execute(self, keywords: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Search for articles based on keywords
        
        Args:
            keywords: List of keywords to search for
            
        Returns:
            List[Dict]: List of article data
        """
        logger.info(f"Searching for articles with keywords: {keywords}")
        
        # For now, we'll use Ollama to generate simulated article results
        # In a real implementation, this would connect to Google News or another search API
        
        # Create messages for Ollama
        messages = [
            OllamaMessage(
                role="system",
                content="""You are an article search and generation system that simulates 
                search results based on provided keywords.
                
                For the given keywords, generate 3-5 realistic article summaries that might 
                be found in a search. Include diverse perspectives - some supporting common views
                on the topic and others presenting alternative or opposing viewpoints.
                
                For each article, provide:
                1. A realistic title
                2. A brief content summary (3-5 sentences)
                3. A simulated URL
                
                Format your response as a JSON array of article objects, each with:
                - "title": string
                - "content": string (the article summary)
                - "url": string (a realistic URL)
                
                Make these articles appear realistic and diverse in viewpoint.
                """
            ),
            OllamaMessage(
                role="user",
                content=f"""Search for articles related to these keywords: {', '.join(keywords)}
                
                Remember to provide diverse perspectives in the articles, including both supporting and 
                opposing viewpoints. Return only the JSON array of articles.
                """
            )
        ]
        
        # Get response from Ollama
        response = self.ollama_client.send_message(messages)
        logger.info(f"Article search received response of length: {len(response.response)}")
        
        # Parse the response to extract articles
        try:
            import json
            import re
            
            # Try to extract just the JSON array using regex in case there's extra text
            json_match = re.search(r'\[.*\]', response.response, re.DOTALL)
            if json_match:
                articles_json = json_match.group(0)
                articles = json.loads(articles_json)
            else:
                # Fallback: try to parse the whole response
                articles = json.loads(response.response)
                
            # Ensure we have a list
            if not isinstance(articles, list):
                logger.warning("Response is not a list, using default articles")
                return self._generate_default_articles(keywords)
                
            # Ensure each article has the required fields
            for article in articles:
                if not isinstance(article, dict):
                    continue
                    
                if "title" not in article:
                    article["title"] = f"Article about {', '.join(keywords)}"
                    
                if "content" not in article:
                    article["content"] = f"This article discusses topics related to {', '.join(keywords)}."
                    
                if "url" not in article:
                    article["url"] = f"https://example.com/article/{'-'.join(keywords)}"
            
            logger.info(f"Returned {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error parsing articles: {e}")
            # Return default articles in case of parsing error
            return self._generate_default_articles(keywords)
    
    def _generate_default_articles(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Generate default articles in case of parsing errors"""
        default_articles = []
        
        for i, keyword in enumerate(keywords):
            default_articles.append({
                "title": f"Understanding {keyword.capitalize()}",
                "content": f"This article provides an overview of {keyword} and its implications. It covers the main aspects and current thinking on the topic.",
                "url": f"https://example.com/article/{keyword.replace(' ', '-')}"
            })
            
            # Add an opposing view for each keyword
            default_articles.append({
                "title": f"Challenging Common Views on {keyword.capitalize()}",
                "content": f"This article presents alternative perspectives on {keyword}, questioning some commonly held assumptions. It offers different ways to think about this topic.",
                "url": f"https://example.com/alternative-view/{keyword.replace(' ', '-')}"
            })
            
        return default_articles
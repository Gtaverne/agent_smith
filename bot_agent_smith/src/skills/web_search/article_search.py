# src/skills/web_search/article_search.py
from dataclasses import dataclass
from typing import List, Dict, Any

from src.core.logger import logger
from src.llm.ollama import OllamaClient, OllamaMessage
from src.orchestration.services.registry import ServiceProtocol
from src.skills.web_search.google_news_fetcher import GoogleNewsFetcher

@dataclass
class ArticleSearchService(ServiceProtocol):
    """Service that searches for articles based on keywords"""
    ollama_client: OllamaClient
    
    def __post_init__(self):
        # Initialize Google News fetcher
        self.news_fetcher = GoogleNewsFetcher(
            delay_between_requests=3.0,  # 3 seconds between requests
            max_articles=5  # Up to 5 articles per search
        )
    
    def execute(self, keywords: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Search for articles based on keywords
        
        Args:
            keywords: List of keywords to search for
            
        Returns:
            List[Dict]: List of article data
        """
        logger.info(f"Searching for articles with keywords: {keywords}")
        
        # Fetch real articles from Google News
        articles = self.news_fetcher.fetch_articles(keywords)
        
        # If we got real articles, use them
        if articles:
            logger.info(f"Found {len(articles)} real articles from Google News")
            
            # Always fetch full content for each article
            for article in articles:
                logger.info(f"Fetching full content for article: {article['title']}")
                content = self.news_fetcher.get_article_content(article["url"])
                if content:
                    article["content"] = content
                    logger.info(f"Retrieved {len(content)} characters of content for: {article['title']}")
                else:
                    logger.warning(f"Failed to retrieve content for: {article['title']}")
            
            return articles
        
        logger.warning("No real articles found, returning empty list")
        return []
import time
import feedparser
import re
import html
from typing import List, Dict, Any, Optional
import requests
from urllib.parse import urlencode
from src.core.logger import logger

class GoogleNewsFetcher:
    """
    A simplified Google News fetcher that uses the RSS feed to get articles
    based on keywords.
    """
    
    def __init__(self, delay_between_requests: float = 2.0, max_articles: int = 5):
        """
        Initialize the Google News fetcher
        
        Args:
            delay_between_requests: Delay in seconds between requests to avoid rate limits
            max_articles: Maximum number of articles to return per search
        """
        self.base_url = "https://news.google.com/rss/search"
        self.delay = delay_between_requests
        self.max_articles = max_articles
        self.last_request_time = 0
    
    def clean_text(self, text: str) -> str:
        """Clean HTML entities and extra whitespace from text."""
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    
    def _apply_rate_limit(self):
        """Apply rate limiting to avoid being blocked by Google"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.delay:
            # Sleep to respect the rate limit
            sleep_time = self.delay - time_since_last_request
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def extract_article_identifier(self, google_url: str) -> Optional[str]:
        """Extract the article identifier from Google News URL"""
        if "news.google.com/articles/" in google_url:
            parts = google_url.split("/articles/")
            if len(parts) > 1:
                return parts[1].split("?")[0]
        return None
    
    def get_real_article_url(self, google_url: str) -> str:
        """
        Try to extract the real URL from a Google News URL by making a request
        and capturing the redirect.
        """
        try:
            # Apply rate limiting
            self._apply_rate_limit()
            
            # Make a HEAD request with redirect disabled to capture the redirect URL
            response = requests.head(
                google_url, 
                allow_redirects=False,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                },
                timeout=5
            )
            
            # If we get a redirect, use the location header as the real URL
            if 300 <= response.status_code < 400 and "location" in response.headers:
                return response.headers["location"]
            
            return google_url
        except Exception as e:
            logger.error(f"Error getting real article URL: {e}")
            return google_url
    
    def fetch_articles(self, keywords: List[str], language: str = "en") -> List[Dict[str, Any]]:
        """
        Fetch articles from Google News based on keywords
        
        Args:
            keywords: List of keywords to search for
            language: Language code (default: 'en')
            
        Returns:
            List of article data dictionaries
        """
        # Construct query from keywords
        query = " ".join(keywords)
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        # Construct parameters for Google News RSS
        params = {
            "q": query,
            "hl": language,
            "gl": "US",
            "ceid": f"US:{language}"
        }
        
        # Construct URL with parameters
        url = f"{self.base_url}?{urlencode(params)}"
        
        logger.info(f"Fetching news for query: {query}")
        
        # Parse the RSS feed
        feed = feedparser.parse(url)
        
        # Process articles
        articles = []
        for entry in feed.entries[:self.max_articles]:
            # Get the article URL - first try to get the real URL
            article_url = self.get_real_article_url(entry.link)
            
            # Extract source if available
            source = entry.source.title if hasattr(entry, "source") else None
            
            # Get content from summary or description
            content = ""
            if hasattr(entry, "summary"):
                content = self.clean_text(entry.summary)
            elif hasattr(entry, "description"):
                content = self.clean_text(entry.description)
            
            # Create article data dictionary
            article_data = {
                "title": self.clean_text(entry.title),
                "url": article_url,
                "source": source,
                "content": content
            }
            
            articles.append(article_data)
            logger.info(f"Found article: {article_data['title']} from {source}")
        
        return articles
    
    def get_article_content(self, url: str) -> Optional[str]:
        """
        Fetch more detailed content from an article URL.
        Uses a simple approach to extract text from HTML.
        """
        # Apply rate limiting
        self._apply_rate_limit()
        
        try:
            # Get the article page
            response = requests.get(
                url, 
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }, 
                timeout=10
            )
            
            # Extract content (simple approach)
            content = response.text
            
            # Remove HTML tags
            content = re.sub(r'<script.*?</script>', ' ', content, flags=re.DOTALL)
            content = re.sub(r'<style.*?</style>', ' ', content, flags=re.DOTALL)
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content).strip()
            
            # Take a reasonable excerpt
            excerpt = content[:1000] + "..." if len(content) > 1000 else content
            return self.clean_text(excerpt)
        except Exception as e:
            logger.error(f"Error fetching article content: {e}")
            return None
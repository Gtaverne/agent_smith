import html
import re
import time
from typing import List, Dict, Any, Optional
import requests
from urllib.parse import urlencode
import feedparser
from playwright.sync_api import sync_playwright
import trafilatura

from src.core.logger import logger
from src.skills.web_search.google_decoder import GoogleDecoder

class GoogleNewsFetcher:
    """
    Enhanced Google News fetcher that uses Google URL decoding and multiple
    content extraction methods to retrieve full article text.
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
        self.decoder = GoogleDecoder()
    
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
    
    def get_real_article_url(self, google_url: str) -> str:
        """
        Get the real article URL from a Google News URL by decoding it
        """
        logger.info(f"Decoding Google News URL: {google_url}")
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        # Use the decoder to get the real URL
        result = self.decoder.decode_google_news_url(google_url)
        
        if result.get("status"):
            real_url = result["decoded_url"]
            logger.info(f"Successfully decoded URL: {real_url}")
            return real_url
        else:
            logger.warning(f"Failed to decode Google URL: {result.get('message')}")
            return google_url  # Return original URL as fallback
    
    def get_article_content_with_playwright(self, url: str) -> Optional[str]:
        """Use Playwright to fetch article content for JavaScript-heavy sites"""
        logger.info(f"Using Playwright to fetch content from: {url}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    content = page.content()
                    
                    # Try to extract article content with trafilatura
                    article_text = trafilatura.extract(content, include_comments=False, 
                                                     output_format='txt')
                    
                    if article_text and len(article_text) > 100:
                        logger.info(f"Extracted {len(article_text)} chars with Playwright+Trafilatura")
                        return article_text
                    
                    # Fallback to getting all text if trafilatura fails
                    text = page.evaluate('() => document.body.innerText')
                    logger.info(f"Extracted {len(text)} chars with Playwright body text")
                    return text
                finally:
                    browser.close()
        except Exception as e:
            logger.error(f"Playwright error: {str(e)}")
            return None
    
    def get_article_content(self, url: str) -> Optional[str]:
        """Fetch full article content using a tiered extraction approach"""
        # Apply rate limiting
        self._apply_rate_limit()
        logger.info(f"Crawling full content from: {url}")
        
        # Try Trafilatura first (best for article extraction)
        try:
            import trafilatura
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                # Fix the format parameter - 'text' should be 'txt'
                article_text = trafilatura.extract(downloaded, include_comments=False, 
                                                include_tables=False, output_format='txt')
                if article_text and len(article_text) > 100:
                    logger.info(f"Successfully extracted article using Trafilatura ({len(article_text)} chars)")
                    return article_text
        except Exception as e:
            logger.warning(f"Trafilatura extraction failed: {e}")
        
        # Try handling Google consent pages
        if "consent.google.com" in url:
            try:
                actual_url = self._extract_actual_url_from_consent(url)
                if actual_url and actual_url != url:
                    logger.info(f"Extracted actual URL from consent page: {actual_url}")
                    return self.get_article_content(actual_url)
            except Exception as e:
                logger.warning(f"Failed to extract URL from consent page: {e}")
        
        # Try Newspaper3k second
        try:
            import newspaper
            from newspaper import Article
            article = Article(url)
            article.download()
            article.parse()
            if article.text and len(article.text) > 100:
                logger.info(f"Successfully extracted article using Newspaper3k ({len(article.text)} chars)")
                return article.text
        except Exception as e:
            logger.warning(f"Newspaper3k extraction failed: {e}")
        
        # Try Playwright for JavaScript-heavy sites
        playwright_content = self.get_article_content_with_playwright(url)
        if playwright_content:
            return playwright_content
            
        # Basic fallback using direct HTTP request
        return self._basic_html_extraction(url)
    
    def _extract_actual_url_from_consent(self, consent_url: str) -> Optional[str]:
        """Extract the actual article URL from a Google consent page"""
        try:
            import re
            # Find the continue parameter in the URL
            match = re.search(r'continue=([^&]+)', consent_url)
            if match:
                from urllib.parse import unquote
                actual_url = unquote(match.group(1))
                return actual_url
            return None
        except Exception as e:
            logger.warning(f"Error extracting URL from consent: {e}")
            return None
            
    def _basic_html_extraction(self, url: str) -> Optional[str]:
        """Basic HTML extraction method (your original implementation)"""
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
            
            # Return the full content instead of truncating
            logger.info(f"Extracted {len(content)} chars with basic HTML extraction")
            return self.clean_text(content)
        except Exception as e:
            logger.error(f"Error with basic HTML extraction: {e}")
            return None
    
    def fetch_articles(self, keywords: List[str], language: str = "en") -> List[Dict[str, Any]]:
        """
        Search for articles based on keywords
        
        Args:
            keywords: List of keywords to search for
            language: Language code (default: 'en')
            
        Returns:
            List[Dict]: List of article data
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
            # Get the real article URL
            try:
                article_url = self.get_real_article_url(entry.link)
            except Exception as e:
                logger.error(f"Error decoding URL: {str(e)}")
                article_url = entry.link  # Use Google URL as fallback
            
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
            
            # Get full content
            logger.info(f"Fetching full content for article: {article_data['title']}")
            full_content = self.get_article_content(article_url)
            if full_content:
                article_data["content"] = full_content
                logger.info(f"Retrieved {len(full_content)} characters of content")
            else:
                logger.warning(f"Failed to retrieve content for: {article_data['title']}")
        
        return articles
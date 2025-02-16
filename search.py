import html
import os
import re
from datetime import datetime

import feedparser
import requests
from anthropic import Anthropic
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from loguru import logger
from newspaper import Article
from newspaper.article import ArticleException
from rich import print as rprint

load_dotenv()

DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "1")
MAX_ARTICLES = 2
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])


class GoogleNewsFetcher:
    def __init__(self):
        self.base_url = "https://news.google.com/rss/search"

    def clean_text(self, text: str) -> str:
        """Clean HTML entities and extra whitespace from text."""
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def get_real_url(self, google_url: str) -> str | None:
        """Follow Google News redirect to get the actual article URL."""
        try:
            response = requests.get(google_url, allow_redirects=True, timeout=10)
            return response.url
        except Exception as e:
            print(f"Error following redirect: {str(e)}")
            return None

    def fetch_article_content(self, url: str) -> dict | None:
        """
        Fetch and parse article content using multiple methods.

        Args:
            url (str): Article URL

        Returns:
            Optional[Dict]: Parsed article data or None if all methods fail
        """
        # Try Firecrawl first
        try:
            response = app.scrape_url(url=url, params={"formats": ["markdown"]})
            breakpoint()
            if response.get("markdown"):
                logger.info(
                    f"Firecrawl response (first 100 characters): {response['markdown'][:10]}"
                )
                return {"text": response["markdown"], "source": "firecrawl"}
        except Exception as e:
            logger.warning(f"Firecrawl failed for {url}: {str(e)}")

        # If Firecrawl fails, try newspaper3k
        try:
            article = Article(url, language="fr")
            article.download()
            article.parse()
            article.nlp()  # Enables summary and keywords extraction

            return {
                "text": article.text,
                "summary": article.summary,
                "keywords": article.keywords,
                "authors": article.authors,
                "publish_date": article.publish_date.isoformat()
                if article.publish_date
                else None,
                "source": "newspaper3k",
            }

        except ArticleException as e:
            logger.error(f"Error parsing article {url} with newspaper3k: {str(e)}")

        # If all methods fail, return None
        logger.error(f"Failed to fetch content from {url} using all available methods.")
        return None

    def fetch_articles(self, query: str, language: str = "fr") -> list[dict]:
        """
        Fetch articles from Google News based on a search query.

        Args:
            query (str): Search query
            language (str): Language code (default: 'fr')

        Returns:
            list[dict]: list of articles with title, link, and publication date
        """
        params = {"q": query, "hl": language, "gl": "FR", "ceid": f"FR:{language}"}

        try:
            feed = feedparser.parse(
                f"{self.base_url}?{requests.compat.urlencode(params)}"
            )
            articles = []
            for entry in feed.entries[:MAX_ARTICLES]:
                article = {
                    "title": self.clean_text(entry.title),
                    "link": entry.link,
                    "published": datetime.strptime(
                        entry.published, "%a, %d %b %Y %H:%M:%S %Z"
                    ).isoformat(),
                    "real_link": fetcher.get_real_url(entry.link),
                    "source": entry.source.title if hasattr(entry, "source") else None,
                }
                articles.append(article)
                logger.info(f"Real Link: {fetcher.get_real_url(article['link'])}")
            return articles

        except Exception as e:
            logger.error(f"Error fetching articles: {str(e)}")
            return []


# Usage example
if __name__ == "__main__":
    import argparse
    import json
    import os
    from datetime import datetime

    parser = argparse.ArgumentParser(
        description="Fetch news articles based on a search query."
    )
    parser.add_argument("--query", type=str, help="Search query for news articles")
    args = parser.parse_args()

    query = "intelligence artificielle éthique"
    if args.query:
        query = args.query
    else:
        user_input = input("Enter your search query: ")
        if user_input:
            query = user_input

    fetcher = GoogleNewsFetcher()

    logger.info("Fetching articles...")
    articles = fetcher.fetch_articles(query)

    query_results = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "articles": [],
    }

    for article in articles:
        rprint(f"\nTitle: {article['title']}")
        rprint(f"Source: {article['source']}")
        rprint(f"Published: {article['published']}")
        rprint(f"Link: {article['link']}")
        article_content = fetcher.fetch_article_content(article["link"])

        article_data = {
            "title": article["title"],
            "source": article["source"],
            "published": article["published"],
            "link": article["link"],
            "scraped_content": article_content.get("text", "")
            if article_content
            else "",
            "scraping_method": article_content.get("source", "none")
            if article_content
            else "none",
        }

        if article_content:
            article_data.update(
                {
                    "summary": article_content.get("summary"),
                    "keywords": article_content.get("keywords"),
                    "authors": article_content.get("authors"),
                    "publish_date": article_content.get("publish_date"),
                }
            )
            logger.info(
                f"Successfully fetched content from {article['link']} using {article_data['scraping_method']}."
            )
        else:
            logger.error(
                f"Failed to fetch content from {article['link']} using all available methods."
            )

        query_results["articles"].append(article_data)

    # Create data folder if it doesn't exist
    os.makedirs("data", exist_ok=True)

    # Save query results to a JSON file
    filename = f"data/query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(query_results, f, ensure_ascii=False, indent=2)

    logger.info(f"Query results saved to {filename}")

import html
import json
import os
import re
import time
from datetime import datetime
from urllib.parse import quote, urlparse

import feedparser
import requests
from dotenv import load_dotenv
from loguru import logger
from playwright.sync_api import sync_playwright
from rich import print as rprint
from selectolax.parser import HTMLParser

load_dotenv()

DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "1")
MAX_ARTICLES = 5


def fetch_with_playwright(url: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=300)
            content = page.content()
            return {"text": content, "source": "playwright"}
        except Exception as e:
            logger.error(f"Playwright error: {str(e)}")
            return {}
        finally:
            browser.close()


class GoogleDecoder:
    def __init__(self, proxy=None):
        """
        Initialize the GoogleDecoder class.

        Parameters:
            proxy (str, optional): Proxy to be used for all requests.
                                  Supported formats:
                                  - HTTP/HTTPS: http://user:pass@host:port
                                  - SOCKS5: socks5://user:pass@host:port
                                  - IP and Port: http://host:port
        """
        self.proxy = proxy
        self.proxies = {"http": proxy, "https": proxy} if proxy else None

    def get_base64_str(self, source_url):
        """
        Extracts the base64 string from a Google News URL.

        Parameters:
            source_url (str): The Google News article URL.

        Returns:
            dict: A dictionary containing 'status' and 'base64_str' if successful,
                  otherwise 'status' and 'message'.
        """
        try:
            url = urlparse(source_url)
            path = url.path.split("/")
            if (
                url.hostname == "news.google.com"
                and len(path) > 1
                and path[-2] in ["articles", "read"]
            ):
                return {"status": True, "base64_str": path[-1]}
            return {"status": False, "message": "Invalid Google News URL format."}
        except Exception as e:
            return {"status": False, "message": f"Error in get_base64_str: {str(e)}"}

    def get_decoding_params(self, base64_str):
        """
        Fetches signature and timestamp required for decoding from Google News.
        It first tries to use the URL format https://news.google.com/articles/{base64_str},
        and falls back to https://news.google.com/rss/articles/{base64_str} if any error occurs.

        Parameters:
            base64_str (str): The base64 string extracted from the Google News URL.

        Returns:
            dict: A dictionary containing 'status', 'signature', 'timestamp', and 'base64_str' if successful,
                  otherwise 'status' and 'message'.
        """
        # Try the first URL format.
        try:
            url = f"https://news.google.com/articles/{base64_str}"
            response = requests.get(url, proxies=self.proxies)
            response.raise_for_status()

            parser = HTMLParser(response.text)
            data_element = parser.css_first("c-wiz > div[jscontroller]")
            if data_element is None:
                return {
                    "status": False,
                    "message": "Failed to fetch data attributes from Google News with the articles URL.",
                }

            return {
                "status": True,
                "signature": data_element.attributes.get("data-n-a-sg"),
                "timestamp": data_element.attributes.get("data-n-a-ts"),
                "base64_str": base64_str,
            }

        except requests.exceptions.RequestException:
            # If an error occurs, try the fallback URL format.
            try:
                url = f"https://news.google.com/rss/articles/{base64_str}"
                response = requests.get(url, proxies=self.proxies)
                response.raise_for_status()

                parser = HTMLParser(response.text)
                data_element = parser.css_first("c-wiz > div[jscontroller]")
                if data_element is None:
                    return {
                        "status": False,
                        "message": "Failed to fetch data attributes from Google News with the RSS URL.",
                    }

                return {
                    "status": True,
                    "signature": data_element.attributes.get("data-n-a-sg"),
                    "timestamp": data_element.attributes.get("data-n-a-ts"),
                    "base64_str": base64_str,
                }

            except requests.exceptions.RequestException as rss_req_err:
                return {
                    "status": False,
                    "message": f"Request error in get_decoding_params with RSS URL: {str(rss_req_err)}",
                }
        except Exception as e:
            return {
                "status": False,
                "message": f"Unexpected error in get_decoding_params: {str(e)}",
            }

    def decode_url(self, signature, timestamp, base64_str):
        """
        Decodes the Google News URL using the signature and timestamp.

        Parameters:
            signature (str): The signature required for decoding.
            timestamp (str): The timestamp required for decoding.
            base64_str (str): The base64 string from the Google News URL.

        Returns:
            dict: A dictionary containing 'status' and 'decoded_url' if successful,
                  otherwise 'status' and 'message'.
        """
        try:
            url = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
            payload = [
                "Fbv4je",
                f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{base64_str}",{timestamp},"{signature}"]',
            ]
            headers = {
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            }

            response = requests.post(
                url,
                headers=headers,
                data=f"f.req={quote(json.dumps([[payload]]))}",
                proxies=self.proxies,
            )
            response.raise_for_status()

            parsed_data = json.loads(response.text.split("\n\n")[1])[:-2]
            decoded_url = json.loads(parsed_data[0][2])[1]

            return {"status": True, "decoded_url": decoded_url}
        except requests.exceptions.RequestException as req_err:
            return {
                "status": False,
                "message": f"Request error in decode_url: {str(req_err)}",
            }
        except (json.JSONDecodeError, IndexError, TypeError) as parse_err:
            return {
                "status": False,
                "message": f"Parsing error in decode_url: {str(parse_err)}",
            }
        except Exception as e:
            return {"status": False, "message": f"Error in decode_url: {str(e)}"}

    def decode_google_news_url(self, source_url, interval=None):
        """
        Decodes a Google News article URL into its original source URL.

        Parameters:
            source_url (str): The Google News article URL.
            interval (int, optional): Delay time in seconds before decoding to avoid rate limits.

        Returns:
            dict: A dictionary containing 'status' and 'decoded_url' if successful,
                  otherwise 'status' and 'message'.
        """
        try:
            base64_response = self.get_base64_str(source_url)
            if not base64_response["status"]:
                return base64_response

            decoding_params_response = self.get_decoding_params(
                base64_response["base64_str"]
            )
            if not decoding_params_response["status"]:
                return decoding_params_response

            decoded_url_response = self.decode_url(
                decoding_params_response["signature"],
                decoding_params_response["timestamp"],
                decoding_params_response["base64_str"],
            )
            if interval:
                time.sleep(interval)

            return decoded_url_response
        except Exception as e:
            return {
                "status": False,
                "message": f"Error in decode_google_news_url: {str(e)}",
            }


class GoogleNewsFetcher:
    def __init__(self):
        self.base_url = "https://news.google.com/rss/search"

    def clean_text(self, text: str) -> str:
        """Clean HTML entities and extra whitespace from text."""
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def get_real_url(self, google_url: str) -> str | None:
        """Extract and decode the actual article URL from Google News URL."""
        try:
            print(google_url)
            decoder = GoogleDecoder()
            decoded_url = decoder.decode_google_news_url(google_url, interval=5)
            if decoded_url.get("status"):
                print("Decoded URL:", decoded_url["decoded_url"])
            else:
                print("Error:", decoded_url)
            return decoded_url["decoded_url"]
        except Exception as e:
            logger.error(f"Error decoding Google News URL: {str(e)}")
            return None

    def fetch_article_content(self, url: str) -> dict | None:
        """
        Fetch and parse article content using multiple methods.

        Args:
            url (str): Article URL

        Returns:
            Optional[Dict]: Parsed article data or None if all methods fail
        """
        response = app.scrape_url(url=url, params={"formats": ["markdown"]})
        if response.get("markdown"):
            logger.info(
                f"Firecrawl response (first 100 characters): {response['markdown'][:100]}"
            )
            return {"text": response["markdown"], "source": "firecrawl"}
        else:
            logger.error(f"Firecrawl returned empty markdown for {url}")

        # Fallback to Playwright if Firecrawl fails
        try:
            return fetch_with_playwright(url)
        except Exception as e:
            logger.warning(f"Playwright failed for {url}: {str(e)}")

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
                real_url = self.get_real_url(entry.link)
                article = {
                    "title": self.clean_text(entry.title),
                    "google_link": entry.link,
                    "published": datetime.strptime(
                        entry.published, "%a, %d %b %Y %H:%M:%S %Z"
                    ).isoformat(),
                    "link": real_url,
                    "source": entry.source.title if hasattr(entry, "source") else None,
                }
                articles.append(article)
                logger.info(f"Real Link: {real_url}")
            return articles

        except Exception as e:
            logger.error(f"Error fetching articles: {str(e)}")
            return []


def fetch_articles_main(query: str) -> list[dict]:
    fetcher = GoogleNewsFetcher()
    logger.info(f"Fetching articles for query: {query}")
    articles = fetcher.fetch_articles(query)

    results = []
    for article in articles:
        rprint(f"\nTitle: {article['title']}")
        rprint(f"Source: {article['source']}")
        rprint(f"Published: {article['published']}")
        rprint(f"Link: {article['link']}")
        article_content = fetcher.fetch_article_content(article["link"])

        article_data = {
            "title": article["title"],
            "link": article["link"],
            "text": article_content.get("text", "") if article_content else "",
        }

        if article_content:
            logger.info(
                f"Successfully fetched content from {article['link']} using {article_content.get('source', 'unknown')}."
            )
        else:
            logger.error(
                f"Failed to fetch content from {article['link']} using all available methods."
            )

        results.append(article_data)

    return results


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

    articles = fetch_articles_main(query)

    # Create data folder if it doesn't exist
    os.makedirs("data", exist_ok=True)

    # Save query results to a JSON file
    filename = f"data/query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    logger.info(f"Query results saved to {filename}")

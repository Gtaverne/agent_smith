# tests/test_skills/test_web_search/test_article_search.py
import os
from dotenv import load_dotenv

from src.skills.web_search.article_search import ArticleSearchService
from src.llm.ollama import create_ollama_client

def test_article_search_service():
    """Test the article search service"""
    print("\nStarting article search service test...")
    
    # Load environment variables
    load_dotenv()
    
    # Initialize Ollama client
    client = create_ollama_client(
        base_url=os.getenv('OLLAMA_HOST'),
        model=os.getenv('OLLAMA_MODEL')
    )
    
    # Initialize service
    service = ArticleSearchService(
        ollama_client=client
    )
    
    # Test with different keyword sets
    test_keyword_sets = [
        ['artificial intelligence', 'automation', 'jobs'],
        ['climate change', 'policy', 'economy'],
        ['nuclear energy', 'safety', 'alternatives']
    ]
    
    for keywords in test_keyword_sets:
        print(f"\nTesting with keywords: {keywords}")
        
        # Execute search
        articles = service.execute(keywords=keywords)
        
        print(f"Found {len(articles)} articles")
        for i, article in enumerate(articles):
            print(f"  {i+1}. {article['title']}")
            print(f"     URL: {article['url']}")
            print(f"     Content length: {len(article['content'])}")
        
        # Basic assertions
        assert isinstance(articles, list), "Result should be a list"
        assert len(articles) > 0, "Should return at least one article"
        
        # Check article structure
        for article in articles:
            assert 'title' in article, "Article missing title"
            assert 'content' in article, "Article missing content"
            assert 'url' in article, "Article missing URL"
            
            assert len(article['title']) > 0, "Article title should not be empty"
            assert len(article['content']) > 0, "Article content should not be empty"
            assert article['url'].startswith('http'), "URL should be valid"
    
    print("\nAll article search tests passed!")

if __name__ == "__main__":
    test_article_search_service()
import json
import os
from typing import List

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from firecrawl import FirecrawlApp
from loguru import logger
from main import main
from pydantic import BaseModel

load_dotenv()

app = FastAPI(
    title="Counter Arguments API",
    description="API for finding opposing viewpoints to articles",
    version="1.0.0",
)
print("app from app.py", app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
firecrapp = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])


class ArticleInput(BaseModel):
    content: str


class Article(BaseModel):
    title: str
    link: str
    text: str


class OpposingViewResponse(BaseModel):
    summary: str
    articles: List[str]


@app.post("/analyze", response_model=OpposingViewResponse)
async def analyze_article(article: ArticleInput):
    """
    Analyze an article and find opposing viewpoints

    Args:
        article (ArticleInput): Article text to analyze

    Returns:
        OpposingViewResponse: Summary and list of opposing article links
    """
    try:
        # Call the existing pipeline
        # print("article", article)
        logger.info("I pass here as starting point")
        logger.debug(article)
        response = firecrapp.scrape_url(
            url=article.content, params={"formats": ["markdown"]}
        )
        result = main(response["markdown"])
        # Parse the JSON string returned by main()
        logger.debug(result)
        parsed_result = json.loads(result)
        return OpposingViewResponse(
            summary=parsed_result["summary"], articles=parsed_result["articles"]
        )
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500, detail=f"Error processing article: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

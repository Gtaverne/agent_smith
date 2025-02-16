import json
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from main import main
from pydantic import BaseModel

app = FastAPI(
    title="Counter Arguments API",
    description="API for finding opposing viewpoints to articles",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


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
        print(article)
        result = main(article.content)
        # Parse the JSON string returned by main()
        print(result)
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

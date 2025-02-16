from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from main import main
import json
import uvicorn

app = FastAPI(
    title="Counter Arguments API",
    description="API for finding opposing viewpoints to articles",
    version="1.0.0"
)

class ArticleInput(BaseModel):
    text: str

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
        result = main(article.text)
        
        # Parse the JSON string returned by main()
        parsed_result = json.loads(result)
        
        return OpposingViewResponse(
            summary=parsed_result["summary"],
            articles=parsed_result["articles"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing article: {str(e)}"
        )
    
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
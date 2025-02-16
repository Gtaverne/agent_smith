from typing import List, Dict, Tuple

import json

from systemPrompts import systemPromptFindOpposition
from callClaude import call_claude

def main(textMainArticle) -> str:
    """
    Main function for the backend, gates all interactions between the frontend and the backend
    """
    summary = _summarizeMainArticle(textMainArticle)
    articles : List[Dict[str, str]] = _getArticles(summary)
    opposingArguments : List[Tuple[str, Dict]] = _getOppositePointsOfView(textMainArticle, articles)

    opposingText = ""
    opposingArticles = []
    for argu, arti in opposingArguments:
        opposingText += argu
        opposingArticles.append(arti)

    output = _formatOutputForFrontend(opposingArticles, opposingText)
    return output

def _summarizeMainArticle(text: str) -> str:
    """
    Receive the text of the main article and returns the topic to research
    """
    system = "You are an assistant used to summarize a press article. Your mission is to return a single sentence describing the topic of the article."
    return call_claude(system, text)

def _getArticles(summary: str) -> List[Dict[str, str]]:

    """
    Function that calls the fetcher module. TODO connect to fetcher module
    """
    d1 = {"title": "title1", "link":"https://fake.com", "text": "text1"}
    d2 = {"title": "title2", "link":"https://fake.com", "text": "text2"}
    return [d1, d2]

def _getOppositePointsOfView(textMainArticle: str, articles: List[Dict[(str,str)]]) -> List[Tuple[str, Dict]]:
    """
    Returns a list of points opposing the main article along with the article that supports that point
    """
    for index, article in enumerate(articles):
        article["index"] = index+1
    indexToArti = {arti["index"]: arti for arti in articles}

    def _promptElemOneArticle(article: Dict[str, str]) -> str:
        return "{"+f"""
        "index": {article["index"]},
        "title": "{article["title"]}",
        "content": "{article["text"]}"
        """+"}"
    
    jsonListArticles = "[" + ",".join([_promptElemOneArticle(arti) for arti in articles]) + "]"
    textPrompt = f"""{{
        "main_article": {{
            "content": "{textMainArticle}"
        }},
        "list_of_articles": {jsonListArticles}
    }}
    """
    claudeOutput =  call_claude(systemPromptFindOpposition, textPrompt)
    list = json.loads(claudeOutput)
    return [(elem["content"], indexToArti[elem["index"]]) for elem in list]

def _formatOutputForFrontend(opposingArticles: List[Dict[str, str]], finalSummary: str) -> str:
    listArticleLinks = ["\""+arti["link"]+"\"" for arti in opposingArticles]
    json = f"""
    {{
        "summary": "{finalSummary}",
        "articles": [{",".join(listArticleLinks)}]
    }}
    """
    return json

if __name__ == "__main__":
    system = "You are a very good poet, you answer the question given with a haiku"
    text = "What is the meaning of life?"
    # print(call_claude(system, text))

    opposingArticles = [{"title": "title1", "link":"https://fake.com", "text": "text1"}, {"title": "title2", "link":"https://fake.com", "text": "text2"}]
    finalSummary = "This is the final summary"
    print(_formatOutputForFrontend(opposingArticles, finalSummary))

    print(main("This is the main article"))
from typing import List, Dict, Tuple

import json

from systemPrompts import systemPromptFindOpposition
from callClaude import call_claude, call_claude_forceArticleList

from search import fetch_articles_main

def main(textMainArticle) -> str:
    """
    Main function for the backend, gates all interactions between the frontend and the backend
    """
    summary = _summarizeMainArticle(textMainArticle)
    articles : List[Dict[str, str]] = _getArticles(summary)
    print(articles)
    opposingArguments : List[Tuple[str, Dict]] = _getOppositePointsOfView(textMainArticle, articles)
    print(opposingArguments)

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
    system = """You are an assistant used to summarize a press article. 
    Your mission is to return four keywords summarizing the article's topic, separated by commas."""
    return call_claude(system, text)

def _getArticles(summary: str) -> List[Dict[str, str]]:

    """
    Function that calls the fetcher module. TODO connect to fetcher module
    """
    return fetch_articles_main(summary)

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
    claudeOutput =  call_claude_forceArticleList(systemPromptFindOpposition, textPrompt)
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

    TEST_ARTICLE="""Internet search trends in the Washington, DC, metro area have been nothing short of stunning in recent weeks, reflecting what appears to be growing panic within the federal bureaucracy as President Trump and Elon Musk's Department of Government Efficiency (DOGE) root out corruption in non-governmental organizations (NGO) and federal agencies. 

    Earlier this week, internet search trends for "Criminal Defense Lawyer" and "RICO Laws" went viral on X, fueling speculation that Washington's political elites were in panic mode. The searches coincided with DOGE's efforts to neuter USAID's funding of NGOs that propped up a shadow government, as well as begin cutting tens of thousands of workers from various federal agencies.

    DC Internet Searches For "Criminal Defense Lawyer" & "RICO Law" Erupt As DOGE Drains Swamp https://t.co/4ytzi4YcgV

    — zerohedge (@zerohedge) February 13, 2025
    Now, more suspicious search trends have erupted among DC residents as DOGE efforts went into beast mode at the end of the week. 

    "Washington DC searches soar for "Swiss bank" (yellow), "offshore bank" (green), "wire money" (red) and "IBAN" (blue)," WikiLeaks wrote on X late Thursday. 

    Washington DC searches soar for "Swiss bank" (yellow), "offshore bank" (green), "wire money" (red) and "IBAN" (blue) pic.twitter.com/OBEg0hW8g0

    — WikiLeaks (@wikileaks) February 13, 2025
    Search terms "Wipe" (blue) and "Erase" (red) also moved higher in recent weeks. Wipe hard drives?

    Washington DC searches soar for "wipe" (blue) and "erase" (red) according to Google trends data. pic.twitter.com/WTbK1C1zxy

    — WikiLeaks (@wikileaks) February 14, 2025
    Well, yes, the search term "wipe hard drive" across the DC metro has gone absolutely parabolic."""

    system = "You are a very good poet, you answer the question given with a haiku"
    text = "What is the meaning of life?"
    # print(call_claude(system, text))

    # opposingArticles = [{"title": "title1", "link":"https://fake.com", "text": "text1"}, {"title": "title2", "link":"https://fake.com", "text": "text2"}]
    # finalSummary = "This is the final summary"
    # print(_formatOutputForFrontend(opposingArticles, finalSummary))

    print(main(TEST_ARTICLE))
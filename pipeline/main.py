import json
from typing import Dict, List, Tuple

from callClaude import call_claude, call_claude_forceArticleList
from loguru import logger
from search import fetch_articles_main
from systemPrompts import systemPromptFindOpposition


def main(textMainArticle) -> str:
    """
    Main function for the backend, gates all interactions between the frontend and the backend
    """
    summary = _summarizeMainArticle(textMainArticle)
    logger.info(f"Summarized main article: {summary}")

    articles: List[Dict[str, str]] = _getArticles(summary)
    logger.info(f"Retrieved {len(articles)} articles")

    opposingArguments: List[Tuple[str, Dict]] = _getOppositePointsOfView(
        textMainArticle, articles
    )
    logger.info(f"Found {len(opposingArguments)} opposing arguments")

    opposingText = ""
    opposingArticles = []
    for argu, arti in opposingArguments:
        opposingText += argu
        opposingArticles.append(arti)

    output = _formatOutputForFrontend(opposingArticles, opposingText)
    logger.info("Formatted output for frontend")
    return output


def _summarizeMainArticle(text: str) -> str:
    """
    Receive the text of the main article and returns the topic to research
    """
    system = """You are an assistant used to summarize a press article.
    Your mission is to return 3 keywords summarizing the article's topic, separated by commas."""
    output = call_claude(system, text)
    logger.info("Summarized main article")
    return output


def _getArticles(summary: str) -> List[Dict[str, str]]:
    """
    Function that calls the fetcher module. TODO connect to fetcher module
    """
    return fetch_articles_main(summary)


def _getOppositePointsOfView(
    textMainArticle: str, articles: List[Dict[(str, str)]]
) -> List[Tuple[str, Dict]]:
    """
    Returns a list of points opposing the main article along with the article that supports that point
    """
    logger.info(f"Starting _getOppositePointsOfView with {len(articles)} articles")
    for index, article in enumerate(articles):
        article["index"] = index + 1
    indexToArti = {arti["index"]: arti for arti in articles}
    logger.debug(f"Created indexToArti dictionary with {len(indexToArti)} items")

    # Create the input structure as a Python dictionary
    input_data = {
        "main_article": {"content": textMainArticle},
        "list_of_articles": [
            {
                "index": article["index"],
                "title": article["title"],
                "content": article["text"],
            }
            for article in articles
        ],
    }
    logger.debug("Created input_data structure")

    # Let json.dumps handle the escaping
    textPrompt = json.dumps(input_data)
    logger.debug(f"Created textPrompt with length {len(textPrompt)}")
    claudeOutput = call_claude_forceArticleList(systemPromptFindOpposition, textPrompt)
    logger.info("Received response from Claude")
    opposing_list = json.loads(claudeOutput)
    logger.debug(f"Parsed Claude output, found {len(opposing_list)} opposing points")

    result = [
        (elem["contradiction"], indexToArti[elem["index"]]) for elem in opposing_list
    ]
    logger.info(f"Returning {len(result)} opposing points of view")
    return result


def _formatOutputForFrontend(
    opposingArticles: List[Dict[str, str]], finalSummary: str
) -> str:
    # Create the output structure as a Python dictionary
    output_data = {
        "summary": finalSummary,
        "articles": [article["link"] for article in opposingArticles],
    }

    # Let json.dumps handle the escaping
    return json.dumps(output_data)


if __name__ == "__main__":
    TEST_ARTICLE = """

    Internet search trends in the Washington, DC, metro area have been nothing short of stunning in recent weeks, reflecting what appears to be growing panic within the federal bureaucracy as President Trump and Elon Musk's Department of Government Efficiency (DOGE) root out corruption in non-governmental organizations (NGO) and federal agencies.

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
    Well, yes, the search term "wipe hard drive" across the DC metro has gone absolutely parabolic.

"""

    print("\n\n\n")
    print(main(TEST_ARTICLE))

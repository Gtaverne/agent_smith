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

    opposingText = _prettifySummary(opposingText)
    print("oppositeText", opposingText)
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
    opposing_list = claudeOutput #json.loads(claudeOutput)
    logger.debug(f"Parsed Claude output, found {len(opposing_list)} opposing points")

    result = [
        (elem["contradiction"], indexToArti[elem["index"]]) for elem in opposing_list["articles"]
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

def _prettifySummary(summary: str) -> str:
    system = """You are an assistant used to clean up a summary and make it punchier and more engaging. Please just reword the paragraph you receive, do not explain what you did. Also, do not refer to the documents or article mentioned. Do not say "this article says X" and just say "X". """
    return call_claude(system, summary)

if __name__ == "__main__":
    TEST_ARTICLE = """
Talks involving Secretary of State Marco Rubio and two other senior Trump officials would be the first between American and Russian delegations since the start of Russia’s full-scale invasion of Ukraine in February 2022.
Two men in suits sit in a room with ornate decorations.
President Trump with Secretary of State Marco Rubio in the Oval Office on Tuesday.Credit...Eric Lee/The New York Times

    Published Feb. 15, 2025Updated Feb. 16, 2025, 10:38 a.m. ET

Three top foreign policy aides in the Trump administration plan to meet with Russian officials in Saudi Arabia next week to discuss a path to ending the war in Ukraine, the first substantial talks between the superpowers on the conflict.

The meeting would come less than a week after President Trump spoke on the phone with President Vladimir V. Putin of Russia. Mr. Trump told reporters afterward that talks on ending Russia’s war in Ukraine would take place in Saudi Arabia. The plan for meetings next week in Riyadh was described to reporters on Saturday by a person familiar with the schedule who spoke on condition of anonymity to discuss national security concerns.

The meeting will most likely draw criticism from some top Ukrainian officials. President Volodymyr Zelensky of Ukraine said Thursday that his country must be involved in any talks over its own fate, a statement he made after learning about the Trump-Putin call. Ukrainian officials fear Mr. Trump could try to reach a deal with the Russians that would not have strong security guarantees or viable terms for an enduring peace for Ukraine, which has been trying to repel a full-scale Russian invasion for three years.

The top American officials who plan to attend are Marco Rubio, the secretary of state; Mike Waltz, the national security adviser; and Steve Witkoff, the Middle East envoy who also works on Ukraine-Russia issues, the person familiar with the schedule said.

When asked whether any Ukrainian officials would attend, the person did not say — a sign that Ukraine will probably not take part in the talks, despite Mr. Trump’s saying this week that Ukrainians would participate in discussions in Saudi Arabia.

Mr. Rubio and Vice President JD Vance met with Mr. Zelensky at the Munich Security Conference on Friday.

Mr. Rubio, the top American diplomat, spoke Saturday on the phone with Sergey V. Lavrov, the foreign minister of Russia, as Mr. Rubio traveled from Munich to Israel.

The call was the Trump administration’s latest step in reversing the Biden administration’s attempts to isolate Russia diplomatically.

Mr. Rubio “reaffirmed President Trump’s commitment to finding an end to the conflict in Ukraine,” a State Department spokeswoman, Tammy Bruce, said in a written summary of the call. “In addition, they discussed the opportunity to potentially work together on a number of other bilateral issues.”

The Russian summary of the call said the two top diplomats agreed to address barriers to cooperation on a range of issues that had been erected by the Biden administration. It also said the two diplomats would speak regularly and prepare for a summit between their presidents, and the governments would work to restore the work of each other’s diplomatic missions.

In addition, the Russian summary said, “a mutual commitment to interaction on current international issues was outlined, including the settlement around Ukraine, the situation around Palestine and in the Middle East as a whole and in other regional areas.”

Mr. Rubio planned to go to Saudi Arabia and the United Arab Emirates after stopping in Israel on his first trip in the Middle East.  """

    print("\n\n\n")
    print(main(TEST_ARTICLE))

import os

import anthropic
from anthropic import Anthropic
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def call_claude(systemPrompt, text):
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        temperature=0,
        system=systemPrompt,
        messages=[{"role": "user", "content": [{"type": "text", "text": text}]}],
    )
    logger.debug(message)
    output = message.to_dict()["content"][0]["text"]
    return output


def call_claude_forceArticleList(systemPrompt, text):
    message = anthropic.Anthropic().messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        tools=[
            {
                "name": "record_summary",
                "description": "Record summary of an image using well-structured JSON.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "articles": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "index": {
                                        "type": "integer",
                                        "description": "The index of the article.",
                                    },
                                    "contradiction": {
                                        "type": "string",
                                        "description": "A few sentences to describe the main way in which this article contradicts the main article.",
                                    },
                                },
                                "required": ["index", "contradiction"],
                            },
                        }
                    },
                    "required": ["articles"],
                },
            }
        ],
        tool_choice={"type": "tool", "name": "record_summary"},
        system=systemPrompt,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                ],
            }
        ],
    )
    logger.debug(message)
    output = message.to_dict()["content"][0]["input"]
    return output

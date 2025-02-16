import anthropic
from loguru import logger


def call_claude(systemPrompt, text):
    api_key = "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"
    client = anthropic.Anthropic()
    client.api_key = api_key

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
    api_key = "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"
    client = anthropic.Anthropic()
    client.api_key = api_key

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

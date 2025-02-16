import anthropic

def call_claude(systemPrompt, text):
    api_key = "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"
    client = anthropic.Anthropic()
    client.api_key = api_key

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        temperature=0,
        system=systemPrompt,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": text
                    }
                ]
            }
        ]
    )
    output = message.to_dict()["content"][0]["text"]
    return output
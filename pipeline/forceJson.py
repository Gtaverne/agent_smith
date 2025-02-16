import base64
import anthropic
import httpx

image_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
image_media_type = "image/jpeg"
image_data = base64.standard_b64encode(httpx.get(image_url).content).decode("utf-8")

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
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {
                                "type": "integer",
                                "description": "The index of the article."
                            },
                            "title": {
                                "type": "string",
                                "description": "The title of the article."
                            },
                            "contradiction": {
                                "type": "string",
                                "description": "A few sentences to describe the main way in which this article contradicts the main article."
                            }
                        }
                    }
                },
                "required": ["key_colors", "description"],
            },
        }
    ],
    tool_choice={"type": "tool", "name": "record_summary"},
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": image_data,
                    },
                },
                {"type": "text", "text": "Describe this image."},
            ],
        }
    ],
)
print(message)
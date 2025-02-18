from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class OllamaMessage:
    role: str  # system, assistant, or user
    content: str

@dataclass
class OllamaResponse:
    model: str
    created_at: str
    response: str
    done: bool
    context: Optional[List[int]] = None
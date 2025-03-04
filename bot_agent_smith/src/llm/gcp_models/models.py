from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC

@dataclass
class GCPMessage:
    """Represents a message in the GCP conversation."""
    role: str  # system, user, or assistant
    content: str

@dataclass
class GCPResponse:
    """Represents a response from the GCP model."""
    model: str
    created_at: str
    response: str
    done: bool
    context: Optional[List[int]] = None
    metadata: Optional[Dict[str, Any]] = None
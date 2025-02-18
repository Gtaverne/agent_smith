from dataclasses import dataclass
from typing import Dict, Any, Protocol
from datetime import datetime

class ServiceResponse(Protocol):
    """Protocol for service responses"""
    def to_dict(self) -> Dict[str, Any]: ...

@dataclass
class ContextMetadata:
    """Metadata about the context being built"""
    timestamp: datetime
    service_calls: Dict[str, ServiceResponse]
    
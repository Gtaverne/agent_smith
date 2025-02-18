from typing import Dict, Type, Callable, Any, Protocol
from dataclasses import dataclass
from datetime import datetime

class ServiceProtocol(Protocol):
    """Base protocol for services"""
    def execute(self, **kwargs: Any) -> Any: ...

@dataclass
class ServiceMetadata:
    name: str
    description: str
    version: str
    created_at: datetime = datetime.utcnow()

class ServiceRegistry:
    def __init__(self):
        self.services: Dict[str, ServiceProtocol] = {}
        self.metadata: Dict[str, ServiceMetadata] = {}

    def register(
        self,
        name: str,
        service: ServiceProtocol,
        description: str,
        version: str = "1.0.0"
    ):
        """Register a new service"""
        self.services[name] = service
        self.metadata[name] = ServiceMetadata(
            name=name,
            description=description,
            version=version
        )

    def get_service(self, name: str) -> ServiceProtocol:
        """Get a service by name"""
        if name not in self.services:
            raise KeyError(f"Service {name} not found")
        return self.services[name]

    def list_services(self) -> Dict[str, ServiceMetadata]:
        """List all registered services"""
        return self.metadata
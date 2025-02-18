from dataclasses import dataclass
from typing import Any
from src.core.logger import logger
from src.orchestration.services.registry import ServiceProtocol

@dataclass
class DebugService(ServiceProtocol):
    """Service that logs its inputs for debugging LangGraph workflows"""
    name: str

    def execute(self, **kwargs: Any) -> Any:
        """Log inputs and return a dummy response"""
        logger.info(f"[{self.name}] Service called with args:")
        for key, value in kwargs.items():
            logger.info(f"  {key}: {value}")
        
        # Return dummy response
        return {
            "service": self.name,
            "status": "success",
            "inputs": kwargs
        }
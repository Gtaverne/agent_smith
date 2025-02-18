from typing import Dict, Any, List
from dataclasses import dataclass

from src.orchestration.conversation.window import ConversationWindow
from src.orchestration.services.registry import ServiceRegistry

@dataclass
class ContextBuilder:
    service_registry: ServiceRegistry

    def build_context(
        self,
        window: ConversationWindow,
        required_services: List[str] = None
    ) -> Dict[str, Any]:
        """Build a complete context including service calls if specified"""
        # Start with base context
        context = window.get_context()
        
        # Add service responses if required
        if required_services:
            service_responses = {}
            for service_name in required_services:
                service = self.service_registry.get_service(service_name)
                response = service.execute(context=context)
                service_responses[service_name] = response
            
            context["service_responses"] = service_responses
        
        return context
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.core.types import Message, UserProfile

@dataclass
class WorkflowState:
    """State object for conversation workflows"""
    message: Message
    context: Optional[Dict[str, Any]] = None
    user_profile: Optional[UserProfile] = None
    llm_responses: List[str] = field(default_factory=list)
    service_outputs: Dict[str, Any] = field(default_factory=dict)
    skills_used: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    current_node: str = "start"
    
    def dict(self) -> Dict[str, Any]:
        """Convert state to dict for LangGraph"""
        return {
            "message": self.message.to_dict(),
            "context": self.context,
            "user_profile": self.user_profile.to_dict() if self.user_profile else None,
            "llm_responses": self.llm_responses,
            "service_outputs": self.service_outputs,
            "skills_used": self.skills_used,
            "started_at": self.started_at.isoformat(),
            "current_node": self.current_node
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowState':
        """Create state from dict"""
        return cls(
            message=Message.from_dict(data["message"]),
            context=data.get("context"),
            user_profile=UserProfile.from_dict(data["user_profile"]) if data.get("user_profile") else None,
            llm_responses=data.get("llm_responses", []),
            service_outputs=data.get("service_outputs", {}),
            skills_used=data.get("skills_used", []),
            started_at=datetime.fromisoformat(data["started_at"]),
            current_node=data.get("current_node", "start")
        )
from dataclasses import dataclass
from typing import Dict, Optional

from langgraph.graph import StateGraph, END
from src.core.types import Message
from src.orchestration.services.registry import ServiceRegistry
from src.core.logger import logger

from .state import WorkflowState


@dataclass
class QualificationState:
    message: Message
    needs_counterpoints: Optional[bool] = None
    context: Optional[Dict] = None
    
    def dict(self) -> Dict:
        return {
            "message": self.message.to_dict(),
            "needs_counterpoints": self.needs_counterpoints,
            "context": self.context
        }

class QualificationWorkflow:
    def __init__(self, service_registry: ServiceRegistry):
        self.service_registry = service_registry
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        workflow = StateGraph(QualificationState)
        
        # Add nodes
        workflow.add_node("get_context", self._get_context)
        workflow.add_node("qualifier", self._qualify_message)
        
        # Define edges
        workflow.add_edge("get_context", "qualifier")
        workflow.add_edge("qualifier", END)
        
        return workflow
    
    async def _get_context(self, state: Dict) -> Dict:
        """Get conversation context for the message"""
        current_state = QualificationState(**state)
        
        context_service = self.service_registry.get_service("context")
        current_state.context = context_service.execute(current_state.message)
        
        return current_state.dict()
    
    async def _qualify_message(self, state: Dict) -> Dict:
        """Qualify the message using context"""
        current_state = QualificationState(**state)
        
        qualifier = self.service_registry.get_service("qualifier")
        current_state.needs_counterpoints = qualifier.execute(
            message=current_state.message,
            context=current_state.context
        )
        
        return current_state.dict()
    
    async def execute(self, message: Message) -> bool:
        initial_state = QualificationState(message=message)
        final_state = await self.workflow.ainvoke(initial_state.dict())
        return final_state.get("needs_counterpoints", False)
    
@dataclass
class ConversationWorkflow:
    """Manages conversation workflows using LangGraph"""
    service_registry: ServiceRegistry
    
    def __post_init__(self):
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create the workflow graph"""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("get_context", self._get_context)
        workflow.add_node("generate_response", self._generate_response)
        
        # Define edges - simple linear flow
        workflow.add_edge("get_context", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow
    
    async def _get_context(self, state: Dict) -> Dict:
        """Get conversation context"""
        current_state = WorkflowState.from_dict(state)
        logger.info(f"Getting context for message {current_state.message.id}")
        
        context_service = self.service_registry.get_service("context")
        current_state.context = context_service.execute(current_state.message)
        current_state.current_node = "get_context"
        
        return current_state.dict()
    
    async def _generate_response(self, state: Dict) -> Dict:
        """Generate response using LLM"""
        current_state = WorkflowState.from_dict(state)
        logger.info("Generating response using LLM")
        
        llm_service = self.service_registry.get_service("llm")
        
        # Prepare context for LLM
        context = current_state.context
        conversation_history = context.get("messages", []) if context else []
        
        messages = [
            {
                "role": "system",
                "content": f"""You are Agent Smith, an AI assistant.
                Your goal is to provide helpful and concise responses.
                
                User profile:
                {context.get('user', 'No user profile available')}
                """
            }
        ]
        
        # Add conversation history
        for msg in conversation_history[-3:]:  # Last 3 messages for context
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
            
        # Add current message
        messages.append({
            "role": "user",
            "content": current_state.message.content
        })
        
        # Get response from LLM
        response = llm_service.execute(messages=messages)
        current_state.llm_responses.append(response)
        current_state.current_node = "generate_response"
        
        logger.info("Generated response from LLM")
        logger.debug(f"Response: {response[:100]}...")
        
        return current_state.dict()
    
    async def execute(self, state: WorkflowState) -> str:
        """Execute the workflow for a message"""
        logger.info("========== WORKFLOW EXECUTION ==========")
        logger.info(f"Starting workflow for message: {state.message.content[:100]}...")
        
        logger.info("Running workflow through LangGraph")
        final_state = await self.workflow.ainvoke(state.dict())
        
        final_state_obj = WorkflowState.from_dict(final_state)
        
        if final_state_obj.llm_responses:
            logger.info("Workflow completed with response")
            logger.info(f"Final response: {final_state_obj.llm_responses[-1][:100]}...")
        else:
            logger.warning("Workflow completed without response")
            
        logger.info("========== WORKFLOW COMPLETE ==========")
        
        return final_state_obj.llm_responses[-1] if final_state_obj.llm_responses else ""
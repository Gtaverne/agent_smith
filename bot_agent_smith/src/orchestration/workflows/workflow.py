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
        final_state = await self.workflow.arun(initial_state.dict())
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
        workflow.add_node("analyze_intent", self._analyze_intent)
        workflow.add_node("select_skills", self._select_skills)
        workflow.add_node("execute_skills", self._execute_skills)
        workflow.add_node("generate_response", self._generate_response)
        
        # Define edges
        workflow.add_edge("get_context", "analyze_intent")
        workflow.add_edge("analyze_intent", "select_skills")
        workflow.add_edge("select_skills", "execute_skills")
        workflow.add_edge("execute_skills", "generate_response")
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
    
    async def _analyze_intent(self, state: Dict) -> Dict:
        """Analyze message intent using LLM"""
        current_state = WorkflowState.from_dict(state)
        logger.info("Analyzing message intent")
        
        llm_service = self.service_registry.get_service("llm")
        messages = [
            {
                "role": "system",
                "content": "Analyze the user's intent and categorize it into one of these types: QUESTION, STATEMENT, REQUEST, CHAT"
            },
            {
                "role": "user",
                "content": current_state.message.content
            }
        ]
        
        intent_analysis = llm_service.execute(messages=messages)
        current_state.service_outputs["intent"] = intent_analysis
        current_state.current_node = "analyze_intent"
        
        return current_state.dict()
    
    async def _select_skills(self, state: Dict) -> Dict:
        """Select appropriate skills based on intent"""
        current_state = WorkflowState.from_dict(state)
        logger.info("Selecting skills based on intent")
        
        # Get intent from previous step
        intent = current_state.service_outputs["intent"]
        
        # Use LLM to select appropriate skills
        llm_service = self.service_registry.get_service("llm")
        messages = [
            {
                "role": "system",
                "content": """Based on the message intent, select appropriate skills to use.
                Available skills: vision, web_search, reasoning, context.
                Return a comma-separated list of skill names."""
            },
            {
                "role": "user",
                "content": f"Message: {current_state.message.content}\nIntent: {intent}"
            }
        ]
        
        skills_to_use = llm_service.execute(messages=messages)
        current_state.skills_used = [s.strip() for s in skills_to_use.split(",")]
        current_state.current_node = "select_skills"
        
        return current_state.dict()
    
    async def _execute_skills(self, state: Dict) -> Dict:
        """Execute selected skills"""
        current_state = WorkflowState.from_dict(state)
        logger.info(f"Executing skills: {current_state.skills_used}")
        
        # Execute each selected skill
        for skill_name in current_state.skills_used:
            if skill_name in self.service_registry.services:
                service = self.service_registry.get_service(skill_name)
                result = service.execute(
                    message=current_state.message,
                    context=current_state.context
                )
                current_state.service_outputs[skill_name] = result
        
        current_state.current_node = "execute_skills"
        return current_state.dict()
    
    async def _generate_response(self, state: Dict) -> Dict:
        """Generate final response using LLM"""
        current_state = WorkflowState.from_dict(state)
        logger.info("Generating final response")
        
        # Prepare context for LLM
        skill_outputs = "\n".join(
            f"{skill}: {output}"
            for skill, output in current_state.service_outputs.items()
        )
        
        llm_service = self.service_registry.get_service("llm")
        messages = [
            {
                "role": "system",
                "content": "You are Agent Smith. Generate a response based on the context and skill outputs."
            },
            {
                "role": "user",
                "content": f"""
                User message: {current_state.message.content}
                Context: {current_state.context}
                Skill outputs: {skill_outputs}
                """
            }
        ]
        
        response = llm_service.execute(messages=messages)
        current_state.llm_responses.append(response)
        current_state.current_node = "generate_response"
        
        return current_state.dict()
    
    async def execute(self, message: Message) -> str:
        """Execute the workflow for a message"""
        initial_state = WorkflowState(message=message)
        final_state = await self.workflow.arun(initial_state.dict())
        
        # Return the last LLM response
        final_state_obj = WorkflowState.from_dict(final_state)
        return final_state_obj.llm_responses[-1] if final_state_obj.llm_responses else ""
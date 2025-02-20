from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from src.orchestration.services.registry import ServiceRegistry
from src.core.types import Message  

class WorkflowState(TypedDict):
    message: Message
    context: dict
    response: str
    
def create_workflow(service_registry: ServiceRegistry):
    """Create workflow with service integration"""
    
    def get_context(state: WorkflowState):
        """Get context using ContextService"""
        context_service = service_registry.get_service("context")
        context = context_service.execute(message=state["message"])
        return {"context": context}

    def generate_response(state: WorkflowState):
        """Generate response using LLMService"""
        llm_service = service_registry.get_service("llm")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        
        if state["context"].get("messages"):
            for msg in state["context"]["messages"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        messages.append({
            "role": "user", 
            "content": state["message"].content
        })
        
        response = llm_service.execute(messages=messages)
        return {"response": response}

    workflow = StateGraph(WorkflowState)
    workflow.add_node("get_context", get_context)
    workflow.add_node("generate_response", generate_response)
    workflow.add_edge(START, "get_context")
    workflow.add_edge("get_context", "generate_response")
    workflow.add_edge("generate_response", END)
    
    return workflow.compile()
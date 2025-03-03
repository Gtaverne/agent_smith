from typing_extensions import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from src.orchestration.services.registry import ServiceRegistry
from src.core.types import Message
from src.core.logger import logger

class QualifiedWorkflowState(TypedDict):
    message: Message
    context: dict
    response: str
    needs_counter_arguments: bool
    keywords: list
    articles: list
    counter_arguments: list
    messages_to_send: list
    stage: str  

def create_qualified_workflow(service_registry: ServiceRegistry):
    """
    Create a workflow that first qualifies messages to determine if 
    counter-arguments are needed, then routes to appropriate handling.
    """
    
    def qualify_message(state: QualifiedWorkflowState):
        """Determine if the message needs counter-arguments using QualifierService"""
        # Skip qualification if requested
        if state.get("_skip_qualification", False):
            logger.info("Skipping qualification as requested")
            return {}
            
        logger.info(f"Qualifying message: {state['message'].content[:100]}...")
        
        # Get the qualifier service
        qualifier_service = service_registry.get_service("qualifier")
        
        # Execute qualification
        needs_counter_arguments = qualifier_service.execute(message=state["message"])
        
        logger.info(f"Qualification result: needs_counter_arguments={needs_counter_arguments}")
        
        # If we're only running qualification, return early
        if state.get("_run_qualification_only", False):
            logger.info("Returning after qualification as requested")
            return {"needs_counter_arguments": needs_counter_arguments}
        
        return {"needs_counter_arguments": needs_counter_arguments}
    
    def prepare_acknowledgment(state: QualifiedWorkflowState):
        """Create acknowledgment message for counter-argument search"""
        logger.info("Creating acknowledgment for counter-argument search")
        
        # Initialize or get existing messages array
        messages_to_send = state.get("messages_to_send", [])
        
        # Add acknowledgment message
        messages_to_send.append({
            "content": "🔄 I'm looking for different perspectives on this topic. I'll share what I find shortly...",
            "type": "acknowledgment"
        })
        
        return {"messages_to_send": messages_to_send}

    def get_context(state: QualifiedWorkflowState):
        """Get context using ContextService"""
        logger.info("Getting conversation context...")
        
        context_service = service_registry.get_service("context")
        context = context_service.execute(message=state["message"])
        
        return {"context": context}

    def extract_keywords(state: QualifiedWorkflowState):
        """Extract keywords from the message for article search"""
        logger.info("Extracting keywords for article search...")
        
        keyword_service = service_registry.get_service("keyword_extraction")
        keywords = keyword_service.execute(message_content=state["message"].content)
        
        logger.info(f"Extracted keywords: {keywords}")
        
        return {"keywords": keywords}

    def search_for_articles(state: QualifiedWorkflowState):
        """Search for articles based on extracted keywords"""
        logger.info(f"Searching for articles using keywords: {state['keywords']}")
        
        # Get the article search service
        article_search_service = service_registry.get_service("article_search")
        
        # Execute search
        articles = article_search_service.execute(keywords=state["keywords"])
        
        logger.info(f"Found {len(articles)} articles")
        
        return {"articles": articles}

    def analyze_counter_arguments(state: QualifiedWorkflowState):
        """Analyze articles to find counter-arguments to the message"""
        logger.info("Analyzing articles for counter-arguments...")
        
        articles = state["articles"]
        message_content = state["message"].content
        
        # Use Ollama to identify counter-arguments
        llm_service = service_registry.get_service("llm")
        
        # Prepare system message for counter-argument analysis
        system_message = {
            "role": "system",
            "content": """Analyze the provided articles to find counter-arguments to the main statement.
            
            For each article, determine if it presents a view that contradicts or provides an alternative 
            perspective to the main statement.
            
            Format your response as a JSON array of objects, with each object containing:
            1. "title": A concise title for the counter-argument
            2. "summary": A brief summary of the counter-argument (1-2 sentences)
            3. "article_index": The index of the article containing this counter-argument
            
            Only include counter-arguments that genuinely oppose or offer alternatives to the main statement.
            If an article doesn't provide a counter-argument, don't include it.
            
            Return an empty array if no counter-arguments are found.
            """
        }
        
        # Prepare user message with main statement and articles
        user_message = {
            "role": "user",
            "content": f"""Main statement: "{message_content}"
            
            Articles to analyze:
            {[f"Article {i+1}: {article['title']}\n{article['content']}" for i, article in enumerate(articles)]}
            
            Find counter-arguments in these articles and format as JSON.
            """
        }
        
        # Execute LLM call
        messages = [system_message, user_message]
        response = llm_service.execute(messages=messages)
        
        # Parse the response to extract counter-arguments
        try:
            import json
            import re
            
            # Try to extract just the JSON array using regex in case there's extra text
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                counter_arguments_json = json_match.group(0)
                counter_arguments = json.loads(counter_arguments_json)
            else:
                # Fallback: try to parse the whole response
                counter_arguments = json.loads(response)
                
            # Ensure it's a list
            if not isinstance(counter_arguments, list):
                logger.warning("Response is not a list, using empty list")
                counter_arguments = []
                
            # Add article details to each counter-argument
            for counter_arg in counter_arguments:
                if "article_index" in counter_arg and 0 <= counter_arg["article_index"] < len(articles):
                    article = articles[counter_arg["article_index"]]
                    counter_arg["article_title"] = article["title"]
                    counter_arg["article_url"] = article["url"]
                
            logger.info(f"Found {len(counter_arguments)} counter-arguments")
            
            return {"counter_arguments": counter_arguments}
            
        except Exception as e:
            logger.error(f"Error parsing counter-arguments: {e}")
            # Return empty counter-arguments in case of parsing error
            return {"counter_arguments": []}

    def generate_standard_response(state: QualifiedWorkflowState):
        """Generate a standard response using LLMService"""
        logger.info("Generating standard response...")
        
        llm_service = service_registry.get_service("llm")
        messages = [
            {"role": "system", "content": """You are a helpful assistant. 
            Provide clear, concise responses to the user's questions.
            Focus only on the most recent message, not prior conversation.
            """}
        ]
        
        # Only include relevant recent context
        if state["context"].get("messages"):
            # Get last few messages with most recent context
            messages.extend([
                {
                    "role": msg["role"],
                    "content": msg["content"]
                }
                for msg in state["context"]["messages"][-3:]  # Only use last 3 messages
            ])
        
        response = llm_service.execute(messages=messages)
        return {"response": response}

    def generate_counter_argument_response(state: QualifiedWorkflowState):
        """Generate a response that includes counter-arguments"""
        logger.info("Generating response with counter-arguments...")
        
        llm_service = service_registry.get_service("llm")
        counter_arguments = state["counter_arguments"]
        message_content = state["message"].content
        
        # Format counter-arguments for the prompt
        counter_args_text = ""
        if counter_arguments:
            counter_args_text = "Here are some alternative perspectives:\n\n"
            for i, arg in enumerate(counter_arguments):
                counter_args_text += f"{i+1}. **{arg.get('title', 'Alternative Perspective')}**\n"
                counter_args_text += f"{arg.get('summary', 'No summary available')}\n"
                counter_args_text += f"Source: [{arg.get('article_title', 'Article')}]({arg.get('article_url', '#')})\n\n"
        else:
            counter_args_text = "I couldn't find specific counter-arguments, but here's a balanced perspective:\n\n"
        
        # Create system message
        system_message = {
            "role": "system",
            "content": f"""You are a helpful assistant that provides balanced perspectives.

            The user has shared a viewpoint, and you should acknowledge their perspective
            while also presenting alternative views in a respectful manner.
            
            Here is the counter-argument information you should incorporate into your response:
            {counter_args_text}
            
            Format your response in a conversational but informative tone:
            1. Start by mentioning: "🔄 I noticed this topic has different perspectives. Here's a more balanced view:"
            2. Briefly acknowledge the user's perspective
            3. Present the alternative perspectives with their supporting points
            4. Conclude with a balanced summary that doesn't take a definitive stance
            
            Keep your response concise but informative.
            """
        }
        
        # Create user message including original content
        user_message = {
            "role": "user",
            "content": message_content
        }
        
        # Execute LLM call
        messages = [system_message, user_message]
        response = llm_service.execute(messages=messages)
        
        return {"response": response}
    

    # Conditional edge function to route based on qualification and counter-arguments
    def route_by_qualification(state: QualifiedWorkflowState) -> Literal["standard_response", "extract_keywords"]:
        """Route based on qualification result"""
        if state["needs_counter_arguments"]:
            return "extract_keywords"
        else:
            return "standard_response"

    def route_by_counter_arguments(state: QualifiedWorkflowState) -> Literal["counter_argument_response", "standard_response"]:
        """Route based on whether counter-arguments were found"""
        if state.get("counter_arguments") and len(state["counter_arguments"]) > 0:
            return "counter_argument_response"
        else:
            # Fallback to standard response if no counter-arguments found
            return "standard_response"

     # Create the workflow graph
    workflow = StateGraph(QualifiedWorkflowState)
    
    # Add nodes
    workflow.add_node("qualification", qualify_message)
    workflow.add_node("get_context", get_context)
    workflow.add_node("extract_keywords", extract_keywords)
    workflow.add_node("search_for_articles", search_for_articles)
    workflow.add_node("analyze_counter_arguments", analyze_counter_arguments)
    workflow.add_node("standard_response", generate_standard_response)
    workflow.add_node("counter_argument_response", generate_counter_argument_response)
    workflow.add_node("prepare_acknowledgment", prepare_acknowledgment)
    
    # Define edges
    workflow.add_edge(START, "qualification")
    workflow.add_edge("qualification", "get_context")
    
    # Add conditional routing after context
    workflow.add_conditional_edges(
        "get_context",
        route_by_qualification,
        {
            "standard_response": "standard_response",
            "extract_keywords": "prepare_acknowledgment"
        }
    )

    # Define counter-argument workflow path
    workflow.add_edge("prepare_acknowledgment", "extract_keywords")
    workflow.add_edge("extract_keywords", "search_for_articles")
    workflow.add_edge("search_for_articles", "analyze_counter_arguments")
    
    # Route based on counter-arguments
    workflow.add_conditional_edges(
        "analyze_counter_arguments",
        route_by_counter_arguments,
        {
            "counter_argument_response": "counter_argument_response",
            "standard_response": "standard_response"
        }
    )
    
    workflow.add_edge("standard_response", END)
    workflow.add_edge("counter_argument_response", END)
    
    # Compile the workflow
    return workflow.compile()
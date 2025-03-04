import os
from typing import Union, Any, List, Optional, Dict

from src.core.logger import logger

# Import model-specific modules
from .ollama import create_ollama_client, OllamaClient
from .gcp_models import create_gcp_client, GCPClient

# Type alias for all LLM client types
LLMClient = Union[OllamaClient, GCPClient]

def get_default_model() -> str:
    """
    Get the default model family based on environment settings.
    
    Returns:
        str: Default model family (e.g., 'GCP' or 'OLLAMA')
    """
    return os.getenv('DEFAULT_MODEL', 'GCP').upper()

def get_available_models() -> List[str]:
    """
    Get the list of available model families based on environment settings.
    
    Returns:
        List[str]: List of available model families (e.g., ['GCP', 'OLLAMA'])
    """
    models_env = os.getenv('MODELS', '["GCP", "OLLAMA"]')
    import json
    models = json.loads(models_env)
    return [model.upper() for model in models]

def create_llm_client(model_family: Optional[str] = None) -> LLMClient:
    """
    Factory function to create the appropriate LLM client based on environment settings.
    
    Args:
        model_family: The model family to create (e.g., 'GCP' or 'OLLAMA'). 
                    If None, uses DEFAULT_MODEL from environment.
    
    Returns:
        LLM client instance (OllamaClient or GCPClient, etc.)
    
    Raises:
        ValueError: If the model_family is invalid or required environment
                   variables are missing.
    """
    if model_family is None:
        model_family = get_default_model()
    
    model_family = model_family.upper()
    logger.info(f"Initializing LLM client for model family: {model_family}")
    
    if model_family == 'GCP':
        api_key = os.getenv('GEMINI_API_KEY')
        model = os.getenv('GCP_MODEL', 'gemini-1.0-pro')
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
            
        logger.info(f"Creating GCP client with model: {model}")
        return create_gcp_client(api_key=api_key, model=model)
        
    elif model_family == 'OLLAMA':
        base_url = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        model = os.getenv('OLLAMA_MODEL', 'qwen2.5')
        
        logger.info(f"Creating Ollama client with model: {model} at {base_url}")
        return create_ollama_client(base_url=base_url, model=model)
        
    else:
        raise ValueError(f"Unsupported model family: {model_family}. " +
                         "Please set DEFAULT_MODEL environment variable to GCP or OLLAMA.")

def create_default_llm_client() -> LLMClient:
    """
    Factory function to create the default LLM client based on environment settings.
    
    Returns:
        LLM client instance (OllamaClient or GCPClient, etc.)
    """
    return create_llm_client(get_default_model())

def get_model_configs() -> Dict[str, Dict[str, Any]]:
    """
    Get the configuration for each model family.
    
    Returns:
        Dict mapping model family to configuration
    """
    configs = {}
    
    # GCP config
    configs['GCP'] = {
        'model': os.getenv('GCP_MODEL', 'gemini-2.0-flash-lite'),
        'api_key': os.getenv('GEMINI_API_KEY')
    }
    
    # OLLAMA config
    configs['OLLAMA'] = {
        'base_url': os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
        'model': os.getenv('OLLAMA_MODEL', 'qwen2.5')
    }
    
    return configs
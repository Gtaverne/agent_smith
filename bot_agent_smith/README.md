# Agent Smith Bot

A Discord bot built using Model-Context-Protocol architecture and LangGraph for workflow orchestration.

## Features

- Discord integration for natural conversation
- Qualification of messages to determine if counter-arguments are needed
- Different response paths based on qualification
- ChromaDB for message and user persistence
- Ollama integration for LLM capabilities

## Architecture

- **Interfaces**: Discord adapter for communication
- **Agent**: Manages workflows and state
- **Services/Skills**: 
  - Context management
  - LLM integration
  - Message qualification

## Setup Instructions

### Prerequisites

- Python 3.9+
- Docker (for ChromaDB)
- Ollama running locally

### Installation

1. Clone the repository
2. Set up a Python virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies using uv:
   ```
   pip install uv
   uv pip install -r requirements.txt
   ```

4. Start ChromaDB:
   ```
   cd docker_chroma
   docker-compose up -d
   ```

5. Create a `.env` file with the following variables:
   ```
   DISCORD_TOKEN=your_discord_token
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=qwen2.5
   CHROMA_HOST=localhost
   CHROMA_PORT=8184
   ```

### Running the Bot

```bash
python main.py
```

### Running Tests

```bash
# Test the qualifier service
python tests/test_skills/test_counterpoints/test_qualifier.py

# Test the qualified workflow
python tests/test_workflows/test_qualified_workflow.py
```

## Workflow Description

1. **Message Qualification**: Each message is analyzed to determine if it contains claims that would benefit from counter-arguments
2. **Context Retrieval**: Conversation context is retrieved 
3. **Response Generation**:
   - If qualification determines counter-arguments are needed, a response acknowledging multiple perspectives is generated
   - If no counter-arguments are needed, a standard response is generated

## Adding New Services

1. Create a new service class that implements the `ServiceProtocol`
2. Register the service in the Agent's `__post_init__` method
3. Update workflows to use the new service

## Future Enhancements

- Implement intermediate message responses during processing
- Full counter-argument generation using web search
- Visual content analysis capabilities
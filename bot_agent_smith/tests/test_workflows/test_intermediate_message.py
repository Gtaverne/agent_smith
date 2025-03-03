# tests/test_workflows/test_intermediate_message_workflow.py

import os
import uuid
from datetime import datetime, UTC
from unittest.mock import MagicMock, AsyncMock

# import pytest

from src.core.agent import Agent
from src.core.types import Message, Author, MessageType
from src.interfaces.types import CommunicationEvent, Channel, UserInfo, ChannelType
from src.memory.chroma import ChromaClient, MessageRepository, UserRepository
from src.orchestration.services.registry import ServiceRegistry
from src.llm.ollama import create_ollama_client


# @pytest.mark.asyncio
async def test_intermediate_messages():
    """Test that the workflow sends intermediate messages when counter-arguments are needed"""
    
    # Mock components
    print("\nTesting intermediate messages in qualified workflow...")
    
    # Initialize real services
    chroma = ChromaClient(
        host=os.getenv('CHROMA_HOST', 'localhost'),
        port=int(os.getenv('CHROMA_PORT', '8184'))
    )
    message_repo = MessageRepository(chroma)
    user_repo = UserRepository(chroma)
    
    service_registry = ServiceRegistry()
    
    # Create adapter mock
    adapter_mock = MagicMock()
    adapter_mock.initialize = AsyncMock()
    adapter_mock.start = AsyncMock()
    adapter_mock.stop = AsyncMock()
    adapter_mock.send_message = AsyncMock()
    
    # Create agent with mock adapter
    agent = Agent(
        service_registry=service_registry,
        message_repository=message_repo,
        user_repository=user_repo,
        name="Test Agent",
        agent_id="test-agent-id"
    )
    
    # Register mock adapter
    agent.register_adapter(ChannelType.DISCORD.value, adapter_mock)
    
    # Create test event that should trigger counter-arguments
    counter_argument_event = create_test_event(
        content="Artificial intelligence will inevitably replace all human jobs in the next decade."
    )
    
    # Create test event that should NOT trigger counter-arguments
    simple_event = create_test_event(
        content="What time is it?"
    )
    
    # Start the agent
    await agent.start()
    
    try:
        # Test counter-argument trigger
        print("\nTesting message that should trigger counter-arguments...")
        await agent.handle_event(counter_argument_event)
        
        # Check if intermediate message was sent
        calls = adapter_mock.send_message.call_args_list
        messages_sent = [call.kwargs['content'] for call in calls]
        
        print(f"Number of messages sent: {len(messages_sent)}")
        for i, msg in enumerate(messages_sent):
            print(f"Message {i+1}: {msg[:50]}...")
        
        # We expect at least 2 messages: 
        # 1. The acknowledgment message
        # 2. The final response with counter-arguments
        assert len(messages_sent) >= 2, "Should send at least 2 messages for counter-argument workflow"
        
        # Check content of first message
        assert "looking for different perspectives" in messages_sent[0], "First message should be the acknowledgment"
        
        # Test simple query
        print("\nTesting message that should NOT trigger counter-arguments...")
        adapter_mock.send_message.reset_mock()
        await agent.handle_event(simple_event)
        
        # Check messages sent for simple query
        simple_calls = adapter_mock.send_message.call_args_list
        simple_messages = [call.kwargs['content'] for call in simple_calls]
        
        print(f"Number of messages sent for simple query: {len(simple_messages)}")
        for i, msg in enumerate(simple_messages):
            print(f"Message {i+1}: {msg[:50]}...")
        
        # We expect exactly 1 message for a simple query
        assert len(simple_messages) == 1, "Should send exactly 1 message for simple query"
        
        # First message should NOT be an acknowledgment
        assert "looking for different perspectives" not in simple_messages[0], "Simple query should not trigger acknowledgment"
        
    finally:
        # Stop the agent
        await agent.stop()
        print("\nTest completed")


def create_test_event(content: str) -> CommunicationEvent:
    """Helper to create a test communication event"""
    return CommunicationEvent(
        content=content,
        user=UserInfo(
            user_id="test-user-id",
            username="Test User",
            channel_specific_id="discord-123"
        ),
        channel=Channel(
            type=ChannelType.DISCORD,
            channel_id="test-channel-id"
        ),
        timestamp=datetime.now(UTC),
        event_id=str(uuid.uuid4())
    )


if __name__ == "__main__":
    # For manual test running
    import asyncio
    asyncio.run(test_intermediate_messages())
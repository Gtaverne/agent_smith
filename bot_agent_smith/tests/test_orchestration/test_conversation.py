### File: tests/test_orchestration/test_conversation.py ###

from src.core.types import Message, Author, MessageType
from src.orchestration.conversation.window import ConversationWindow
from datetime import datetime

def test_conversation_window():
    """Test basic conversation window functionality"""
    print("\nTesting conversation window...")
    
    # Create test user
    user = Author(
        id="user123",
        name="Test User",
        discord_id="discord123"
    )
    
    bot = Author(
        id="bot123",
        name="Agent Smith",
        discord_id="bot_456"  # Note: bot discord_id starts with 'bot_'
    )
    
    # Initialize conversation window
    window = ConversationWindow(
        conversation_id="conv123",
        messages=[],
        user_profile=None,
        window_size=3  # Small window for testing
    )
    
    # Add messages and verify window size
    messages = [
        Message(
            content=f"Message {i}",
            type=MessageType.TEXT,
            author=user if i % 2 == 0 else bot,
            conversation_id="conv123"
        )
        for i in range(5)  # Create 5 messages
    ]
    
    print("\nAdding messages to window...")
    for msg in messages:
        window.add_message(msg)
        print(f"Window size after adding message: {len(window.messages)}")
    
    # Verify window size is maintained
    assert len(window.messages) == 3, f"Expected 3 messages, got {len(window.messages)}"
    
    # Verify messages are in correct order (latest 3)
    assert window.messages[-1].content == "Message 4"
    assert window.messages[0].content == "Message 2"
    
    # Get context and verify structure
    context = window.get_context()
    print("\nGenerated context:")
    print(f"Conversation ID: {context['conversation_id']}")
    print("Messages:")
    for msg in context["messages"]:
        print(f"- Role: {msg['role']}, Content: {msg['content']}")
    
    # Verify context format
    assert "conversation_id" in context
    assert "messages" in context
    assert len(context["messages"]) == 3
    
    # Verify message roles are correct
    for i, msg in enumerate(context["messages"]):
        expected_role = "user" if messages[i+2].author.id == "user123" else "assistant"
        assert msg["role"] == expected_role
    
    print("\nAll conversation window tests passed!")

if __name__ == "__main__":
    test_conversation_window()
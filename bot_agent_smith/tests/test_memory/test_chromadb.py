from src.core.types import Message, Author, MessageType, UserProfile
from src.memory.chroma import ChromaClient, MessageRepository, UserRepository
from datetime import datetime
import uuid

def test_chroma_integration():
    print("\nStarting Chroma integration test...")
    
    # Initialize client
    client = ChromaClient(
        host="localhost",
        port=8184
    )
    
    # Initialize repositories
    message_repo = MessageRepository(client)
    user_repo = UserRepository(client)
    
    # Create test user with simple data
    user_id = str(uuid.uuid4())
    test_interests = ["AI", "Python"]
    test_conv_ids = [str(uuid.uuid4())]
    
    user = UserProfile(
        id=user_id,
        name="Test User",
        discord_id="123456789",
        interests=test_interests,
        conversation_ids=test_conv_ids
    )
    
    print(f"\nAdding user: {user.name} with ID: {user.id}")
    user_repo.add(user)
    
    # Create test message
    message_id = str(uuid.uuid4())
    conv_id = str(uuid.uuid4())
    test_attachments = ["file1.txt"]
    
    author = Author(
        id=user.id,
        name=user.name,
        discord_id=user.discord_id
    )
    
    message = Message(
        id=message_id,
        content="Hello, this is a test message",
        type=MessageType.TEXT,
        author=author,
        conversation_id=conv_id,
        attachments=test_attachments
    )
    
    print(f"\nAdding message with ID: {message.id}")
    message_repo.add(message)
    
    # Retrieve and verify user
    retrieved_user = user_repo.get(user.id)
    print(f"\nRetrieved user:")
    print(f"- Name: {retrieved_user.name}")
    print(f"- Discord ID: {retrieved_user.discord_id}")
    print(f"- Interests: {retrieved_user.interests}")
    print(f"- Conversation IDs: {retrieved_user.conversation_ids}")
    
    assert retrieved_user.id == user.id
    assert retrieved_user.name == user.name
    assert retrieved_user.discord_id == user.discord_id
    assert set(retrieved_user.interests) == set(test_interests)
    assert set(retrieved_user.conversation_ids) == set(test_conv_ids)
    
    # Retrieve and verify message
    retrieved_message = message_repo.get(message.id)
    print(f"\nRetrieved message:")
    print(f"- Content: {retrieved_message.content}")
    print(f"- Author: {retrieved_message.author.name}")
    print(f"- Type: {retrieved_message.type}")
    print(f"- Attachments: {retrieved_message.attachments}")
    
    assert retrieved_message.id == message.id
    assert retrieved_message.content == message.content
    assert retrieved_message.type == message.type
    assert retrieved_message.author.id == author.id
    assert retrieved_message.conversation_id == conv_id
    assert set(retrieved_message.attachments) == set(test_attachments)
    
    # Test search
    search_results = message_repo.search("test message")
    print(f"\nSearch results: {len(search_results)} found")
    for msg in search_results:
        print(f"- {msg.content}")
    
        # Cleanup: delete only our test data
        print("\nCleaning up the msg...")
        client.messages.delete(ids=[msg.id])

    print("\nCleaning up the author...")
    client.users.delete(ids=[user.id])
        
    print("\nAll tests passed successfully!")

if __name__ == "__main__":
    test_chroma_integration()
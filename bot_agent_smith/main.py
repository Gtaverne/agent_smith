from src.interfaces.discord.bot import AgentSmithBot
from src.memory import create_vector_db_client, create_message_repository, create_user_repository
from src.core.logger import logger
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    # Get required environment variables
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN not found in environment variables")
    
    # Determine vector DB type from environment variable
    vector_db_type = os.getenv('VECTOR_DB_TYPE', 'chroma').lower()
    logger.info(f"Using vector database type: {vector_db_type}")
    
    # Create vector DB client
    vector_db_client = create_vector_db_client(vector_db_type)
    
    # Create repositories
    message_repository = create_message_repository(vector_db_client)
    user_repository = create_user_repository(vector_db_client)
    
    # Create and run bot with vector DB repositories
    bot = AgentSmithBot(
        message_repository=message_repository,
        user_repository=user_repository
    )
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
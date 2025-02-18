from src.interfaces.discord.bot import AgentSmithBot
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        raise ValueError("DISCORD_TOKEN not found in environment variables")
        
    bot = AgentSmithBot()
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
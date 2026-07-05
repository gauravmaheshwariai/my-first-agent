import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
from dotenv import load_dotenv

load_dotenv()

async def main():
    async for message in query(
        prompt="What files are in this directory?",
        options=ClaudeAgentOptions(allowed_tools=["Bash"])
    ):
        print(message)

asyncio.run(main())
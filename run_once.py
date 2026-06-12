"""Run one investigation from the terminal:
   py run_once.py "Acme Sanctioned Holdings" "example.com"
   .venv/Scripts/Activate.ps1
"""
"""Run one investigation from the terminal:
   python run_once.py "Acme Sanctioned Holdings" "example.com"
"""
import asyncio
import sys
from dotenv import load_dotenv
load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from merchant_risk_agent.agent import root_agent

APP = "merchant_risk_cli"

async def main(name: str, website: str):
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name=APP, session_service=session_service)
    session = await session_service.create_session(app_name=APP, user_id="cli")
    prompt = (
        "Investigate this merchant and return your JSON verdict.\n"
        f"Merchant name: {name}\nWebsite: {website}"
    )
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    async for event in runner.run_async(
        user_id="cli", session_id=session.id, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            print(event.content.parts[0].text or "")

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "Blue Bottle Coffee"
    website = sys.argv[2] if len(sys.argv) > 2 else "bluebottlecoffee.com"
    asyncio.run(main(name, website))
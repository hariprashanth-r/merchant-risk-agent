"""Run the MULTI-AGENT pipeline once from the terminal:
   python run_once_multi.py "Acme Sanctioned Holdings" "example.com"

It prints each stage's output so you can watch the gatherer hand off to the
scorer. The single-agent run_once.py is untouched.
"""
import asyncio
import sys
from dotenv import load_dotenv
load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from merchant_risk_multi.agent import root_agent

APP = "merchant_risk_multi_cli"


async def main(name: str, website: str):
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name=APP, session_service=session_service)
    session = await session_service.create_session(app_name=APP, user_id="cli")
    prompt = (
        "Investigate this merchant.\n"
        f"Merchant name: {name}\nWebsite: {website}"
    )
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    async for event in runner.run_async(
        user_id="cli", session_id=session.id, new_message=message
    ):
        # Each sub-agent (gatherer, then scorer) emits a final response in turn.
        if event.is_final_response() and event.content and event.content.parts:
            text = event.content.parts[0].text or ""
            if text.strip():
                print(f"\n===== {getattr(event, 'author', '?')} =====")
                print(text)


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "Blue Bottle Coffee"
    website = sys.argv[2] if len(sys.argv) > 2 else "bluebottlecoffee.com"
    asyncio.run(main(name, website))

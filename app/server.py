import os
import re
import asyncio
import base64
import json
import logging
import struct

from typing import Any
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from agents import function_tool
from agents.realtime import RealtimeAgent, RealtimeRunner, RealtimeSession, RealtimeSessionEvent

from aci import ACI
from aci.auth import SecurityScheme

# Load environment variables from .env file
load_dotenv()

# Get GitHub username from environment or use default
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")
# Get GitHub token from environment
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@function_tool
def get_weather(city: str) -> str:
    """Get the weather in a city."""
    return f"The weather in {city} is sunny."


@function_tool
def get_secret_number() -> int:
    """Returns the secret number, if the user asks for it."""
    return 71

@function_tool
def add_CalenderEvent(event: str, date: str) -> str:
    """Adds a calendar event."""
    return f"Event '{event}' has been added to your calendar for {date}."

aci = ACI()

# Link GitHub account to ACI
if GITHUB_TOKEN:
    try:
        result = aci.linked_accounts.link(
            app_name="GITHUB",                      # Name of the app to link to
            linked_account_owner_id=GITHUB_USERNAME,  # ID to identify the owner of this linked account
            security_scheme=SecurityScheme.API_KEY,   # Type of authentication
            api_key=GITHUB_TOKEN                     # Required for API_KEY security scheme
        )
        logger.info(f"Successfully linked GitHub account for {GITHUB_USERNAME}")
    except Exception as e:
        logger.error(f"Failed to link GitHub account: {e}")
else:
    logger.warning("GITHUB_TOKEN not set. GitHub account linking skipped.")

github_comment_pr_function = aci.functions.get_definition("GITHUB__CREATE_ISSUE_COMMENT")

@function_tool
def extract_github_info_from_speech(speech_text: str) -> dict:
    """
    Extract GitHub repository name, PR number, and comment from user speech.

    Args:
        speech_text: The transcribed speech text from the user

    Returns:
        A dictionary containing the extracted repository name, PR number, and comment if found,
        or an error message if the information couldn't be extracted
    """
    logger.info("Agent successfully called extract_github_info_from_speech function")

    repo_pattern = r'(?:repository|repo|in)\s+([a-zA-Z0-9_-]+)'
    pr_pattern = r'(?:PR|pull request|issue)\s+#?(\d+)'
    comment_pattern = r'(?:comment|saying|with message)(?:\s+(?:saying|that))?\s+"([^"]+)"|(?:comment|saying|with message)(?:\s+(?:saying|that))?\s+\'([^\']+)\'|(?:comment|saying|with message)\s+(.+?)(?:\s+(?:to|on|in|for)\s+|\s*$)'

    repo_match = re.search(repo_pattern, speech_text, re.IGNORECASE)
    pr_match = re.search(pr_pattern, speech_text, re.IGNORECASE)
    comment_match = re.search(comment_pattern, speech_text, re.IGNORECASE)

    if not repo_match or not pr_match:
        return {
            "success": False,
            "error": "Could not extract GitHub repository name and PR number from speech. Please specify both repository name (e.g., 'repo-name') and PR number (e.g., 'PR 123')."
        }

    repo_name = repo_match.group(1)
    pr_number = pr_match.group(1)

    # Extract comment - check which group matched
    comment = ""
    if comment_match:
        if comment_match.group(1):
            comment = comment_match.group(1)
        elif comment_match.group(2):
            comment = comment_match.group(2)
        elif comment_match.group(3):
            comment = comment_match.group(3)

    if not comment:
        return {
            "success": False,
            "error": "Could not extract comment from speech. Please specify a comment after mentioning the repository and PR number."
        }

    logger.info("Agent successfully completed extraction in extract_github_info_from_speech function")

    return {
        "success": True,
        "repo": repo_name,
        "pr_number": pr_number,
        "comment": comment
    }


@function_tool
def comment_on_github_pr(repo_name: str, pr_number: str, comment: str) -> str:
    """
    Add a comment to a GitHub Pull Request using the repository name and PR number.
    Uses the configured GitHub username from environment variables.
    This function can be called directly with parameters without speech extraction.

    Args:
        repo_name: The name of the GitHub repository
        pr_number: The PR number to comment on
        comment: The comment text to add to the PR

    Returns:
        A confirmation message indicating the comment was added successfully
    """
    # Call the ACI function to add a comment to the PR
    logger.info("Agent successfully called comment_on_github_pr function")

    result = github_comment_pr_function.execute(
        owner=GITHUB_USERNAME,
        repo=repo_name,
        issue_number=pr_number,
        body=comment
    )

    pr_url = f"https://github.com/{GITHUB_USERNAME}/{repo_name}/pull/{pr_number}"
    return f"Comment added to PR {pr_url}: {comment}"

@function_tool
def comment_on_github_pr_from_speech(repo_name: str, pr_number: str, comment: str) -> str:
    """
    Add a comment to a GitHub Pull Request using the repository name and PR number.
    This is a wrapper around comment_on_github_pr for use with speech extraction.

    Args:
        repo_name: The name of the GitHub repository
        pr_number: The PR number to comment on
        comment: The comment text to add to the PR

    Returns:
        A confirmation message indicating the comment was added successfully
    """

    logger.info("Agent successfully called comment_on_github_pr_from_speech function")

    return comment_on_github_pr(repo_name, pr_number, comment)



agent = RealtimeAgent(
    name="Assistant",
    instructions="""You are an assistant that only understands and responds in English. You can help users with various tasks.

        You have the ability to add comments to GitHub Pull Requests when users ask you to do so through speech. 
        
        OPTION 1 - SPEECH EXTRACTION:
        When a user mentions a GitHub repository name, PR number, and a comment in their speech, you should:
        1. Extract the repository name (just the repo name, not owner/repo), PR number, and the comment text from their speech using the extract_github_info_from_speech tool
        2. If the extraction is successful, use the comment_on_github_pr_from_speech tool to add the comment to the PR
        
        OPTION 2 - DIRECT PARAMETER PASSING:
        If you already know the repository name, PR number, and comment (for example, if the user has provided them clearly or you've confirmed them), you can directly use the comment_on_github_pr tool without speech extraction.
        
        The GitHub username is configured in the system, so users only need to specify the repository name, not the owner/username.
        
        Example user requests:
        - "Add a comment to the repository repo-name PR 123 saying 'This looks good to me'"
        - "Comment on pull request 456 in the repo-name repository with 'Please fix the tests'"
        - "Update PR 789 in repo-name with a comment 'Approved with some minor suggestions'"
        
        You should be able to understand and process these requests from speech input.
    """,
    tools=[
        get_weather, 
        get_secret_number, 
        add_CalenderEvent, 
        extract_github_info_from_speech, 
        comment_on_github_pr_from_speech,
        comment_on_github_pr
    ],
)


class RealtimeWebSocketManager:
    def __init__(self):
        self.active_sessions: dict[str, RealtimeSession] = {}
        self.session_contexts: dict[str, Any] = {}
        self.websockets: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.websockets[session_id] = websocket

        runner = RealtimeRunner(
                starting_agent=agent,
                config={
                    "model_settings": {
                        "model_name": "gpt-4o-realtime-preview",
                        "voice": "alloy",
                        "modalities": ["text", "audio"],
                    }
                }
            )

        session_context = await runner.run()
        session = await session_context.__aenter__()
        self.active_sessions[session_id] = session
        self.session_contexts[session_id] = session_context

        # Start event processing task
        asyncio.create_task(self._process_events(session_id))

    async def disconnect(self, session_id: str):
        if session_id in self.session_contexts:
            await self.session_contexts[session_id].__aexit__(None, None, None)
            del self.session_contexts[session_id]
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.websockets:
            del self.websockets[session_id]

    async def send_audio(self, session_id: str, audio_bytes: bytes):
        if session_id in self.active_sessions:
            await self.active_sessions[session_id].send_audio(audio_bytes)

    async def _process_events(self, session_id: str):
        try:
            session = self.active_sessions[session_id]
            websocket = self.websockets[session_id]

            async for event in session:
                event_data = await self._serialize_event(event)
                await websocket.send_text(json.dumps(event_data))
        except Exception as e:
            logger.error(f"Error processing events for session {session_id}: {e}")

    async def _serialize_event(self, event: RealtimeSessionEvent) -> dict[str, Any]:
        base_event: dict[str, Any] = {
            "type": event.type,
        }

        if event.type == "agent_start":
            base_event["agent"] = event.agent.name
        elif event.type == "agent_end":
            base_event["agent"] = event.agent.name
        elif event.type == "handoff":
            base_event["from"] = event.from_agent.name
            base_event["to"] = event.to_agent.name
        elif event.type == "tool_start":
            base_event["tool"] = event.tool.name
        elif event.type == "tool_end":
            base_event["tool"] = event.tool.name
            base_event["output"] = str(event.output)
        elif event.type == "audio":
            base_event["audio"] = base64.b64encode(event.audio.data).decode("utf-8")
        elif event.type == "audio_interrupted":
            pass
        elif event.type == "audio_end":
            pass
        elif event.type == "history_updated":
            base_event["history"] = [item.model_dump(mode="json") for item in event.history]
        elif event.type == "history_added":
            pass
        elif event.type == "guardrail_tripped":
            base_event["guardrail_results"] = [
                {"name": result.guardrail.name} for result in event.guardrail_results
            ]
        elif event.type == "raw_model_event":
            base_event["raw_model_event"] = {
                "type": event.data.type,
            }
        elif event.type == "error":
            base_event["error"] = str(event.error) if hasattr(event, "error") else "Unknown error"
        # else:
        #     assert_never(event)

        return base_event


manager = RealtimeWebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            # print(f"Received message: {message}")

            if message["type"] == "audio":
                # Convert int16 array to bytes
                int16_data = message["data"]
                audio_bytes = struct.pack(f"{len(int16_data)}h", *int16_data)
                print(f"Received audio data of length {len(audio_bytes)} bytes")
                await manager.send_audio(session_id, audio_bytes)

    except WebSocketDisconnect:
        await manager.disconnect(session_id)


app.mount("/", StaticFiles(directory="static", html=True), name="static")


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

import os
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

from agents.realtime import RealtimeAgent, RealtimeRunner, RealtimeSession, RealtimeSessionEvent
from tools import get_weather, get_secret_number, add_calender_event, get_tool

# Load environment variables from .env file
load_dotenv()
LINKED_ACCOUNT_OWNER_ID = os.environ.get("LINKED_ACCOUNT_OWNER_ID")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent = RealtimeAgent(
    name="Assistant",
    instructions="""You are an assistant that only understands and responds in English. You operate in two modes:

    1. Silent Observer Mode (default): In this mode, you should NOT respond to any input.

    2. Active Response Mode: You ONLY enter this mode when you hear the exact trigger phrase "Hey Agent" followed by a task or question.

    Rules:
    - You must ONLY respond when someone says "Hey Agent" followed by a task or question.
    - If the input does not begin with "Hey Agent", remain completely silent and do not respond at all.
    - After you complete a task or answer a question, immediately return to Silent Observer Mode.
    - While in Silent Observer Mode, you should not acknowledge or respond to any input unless it begins with "Hey Agent".
    - You should be able to understand and process requests from speech input.

    Example:
    User: "What's the weather today?"
    You: [No response - remain silent as trigger phrase wasn't used]

    User: "Hey Agent, what's the weather today?"
    You: [Provide weather information]

    User: "Thanks!"
    You: [No response - return to silent mode]""",
    tools=[
        get_weather,
        get_secret_number,
        add_calender_event,
        get_tool("GITHUB__CREATE_ISSUE_COMMENT", LINKED_ACCOUNT_OWNER_ID)
    ]
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
            error_message = str(e)
            logger.error(f"Error processing events for session {session_id}: {error_message}")

            # If this is a linked account error, send a more helpful message to the client
            if "Linked account not found" in error_message and session_id in self.websockets:
                try:
                    app_name = error_message.split("app=")[1].split(",")[0] if "app=" in error_message else "unknown"
                    error_data = {
                        "type": "error",
                        "error": f"Account linking required for {app_name}. Please link your account at https://platform.aci.dev/appconfigs/{app_name}"
                    }
                    await self.websockets[session_id].send_text(json.dumps(error_data))
                except Exception as send_error:
                    logger.error(f"Failed to send error message to client: {send_error}")

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

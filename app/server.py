import asyncio
import base64
import json
import logging
import struct
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agents import function_tool
from agents.realtime import RealtimeAgent, RealtimeRunner, RealtimeSession, RealtimeSessionEvent
from agents import Agent, FunctionTool, RunContextWrapper, Runner
from aci.types.enums import FunctionDefinitionFormat

import os

from collections import Counter

from dotenv import load_dotenv
load_dotenv()

# ACI DEV
from aci import ACI


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

aci = ACI()

# required to cast tool to FunctionTool 
def get_tool(function_name: str, linked_account_owner_id: str) -> FunctionTool:
    function_definition = aci.functions.get_definition(function_name)
    name = function_definition["function"]["name"]
    description = function_definition["function"]["description"]
    parameters = function_definition["function"]["parameters"]

    async def tool_impl(
        ctx: RunContextWrapper[Any], args: str
    ) -> str:
        return aci.handle_function_call(
            function_name,
            json.loads(args),
            linked_account_owner_id=linked_account_owner_id,
            allowed_apps_only=True,
            format=FunctionDefinitionFormat.OPENAI,
        )

    return FunctionTool(
        name=name,
        description=description,
        params_json_schema=parameters,
        on_invoke_tool=tool_impl,
        strict_json_schema=True,
    )


github_agent = RealtimeAgent(
    name="Github Assistant",
    instructions="You are a Github assistant that only understands and responds in English for GitHub issues. Do not respond to any other language. Do not trascribe and traslate.",
    tools=[get_tool("GITHUB__LIST_REPOSITORIES", "personaassis0"),
           get_tool("GITHUB__LIST_ISSUES", "personaassis0"),
           get_tool("GITHUB__CREATE_ISSUE", "personaassis0"),
           get_tool("GITHUB__CREATE_ISSUE_COMMENT", "personaassis0"),
           get_tool("GITHUB__CREATE_PULL_REQUEST", "personaassis0"),
           get_tool("GITHUB__CREATE_PULL_REQUEST", "personaassis0")],
)

brave_agent = RealtimeAgent(
    name="Brave Assistant",
    instructions="You are a Brave Web assistant that only understands and responds in English for GitHub issues. Help wih Brave Browser related queries. Do not respond to any other language. Do not trascribe and traslate.",
    tools=[get_tool("BRAVE_SEARCH__WEB_SEARCH", "brave persona")],
)

slack_agent = RealtimeAgent(
    name="Slack Assistant",
    instructions="You are a Slack assistant that only understands and responds in English for Slack issues. Help with Slack related queries. Do not respond to any other language. Do not trascribe and traslate.",
    tools=[get_tool("SLACK__USERS_LIST", "slack_persona"),
           get_tool("SLACK__CHAT_POST_MESSAGE", "slack_persona") ],
)

google_cal_agent = RealtimeAgent(
    name="Google Calendar Assistant",
    instructions="You are a Google Calendar assistant that only understands and responds in English for Google Calendar issues. Help with Google Calendar related queries. Do not respond to any other language. Do not trascribe and traslate.",
    tools=[get_tool("GOOGLE_CALENDAR__EVENTS_INSERT", "google persona"),
           get_tool("GOOGLE_CALENDAR__EVENTS_LIST", "google persona") ],
)


agent = RealtimeAgent(
    name="Assistant",
    instructions="You are an assistant that only understands and responds in English. Do not respond in any other language" \
                 "You can use tools to answer questions. If you don't know the answer, say 'I don't know'.",
    # tools=[get_tool("GITHUB__GET_USER", "personaassis0"),
    #        get_tool("GITHUB__LIST_ISSUES", "personaassis0"),
    #        get_tool("GITHUB__LIST_REPOSITORIES", "personaassis0") ],
    handoffs=[github_agent, slack_agent, brave_agent, google_cal_agent],
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
        # print(f"Session context created for session {session_context}")
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

def checkAudioData(data):
    if Counter(data)[0]/ len(data) > 0.8:
        return False
    return True


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            # print(f"Received message: {message}")
            if message["type"] == "audio" and checkAudioData(message["data"]):
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

import json
from typing import Any
from dotenv import load_dotenv

from aci import ACI
from aci.types.enums import FunctionDefinitionFormat

from agents import function_tool, FunctionTool, RunContextWrapper

load_dotenv()
aci = ACI()

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

@function_tool
def get_weather(city: str) -> str:
    """Get the weather in a city."""
    return f"The weather in {city} is sunny."


@function_tool
def get_secret_number() -> int:
    """Returns the secret number, if the user asks for it."""
    return 71

@function_tool
def add_calender_event(event: str, date: str) -> str:
    """Adds a calendar event."""
    return f"Event '{event}' has been added to your calendar for {date}."

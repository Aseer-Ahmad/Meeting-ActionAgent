from agents import Agent, FunctionTool, RunContextWrapper, Runner
from aci.types.enums import FunctionDefinitionFormat
import aci
from typing import Any
import json

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



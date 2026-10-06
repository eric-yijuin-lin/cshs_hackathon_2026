import json
from ai.agent.tool_registry import TOOL_REGISTRY

def execute_tool(name: str, arguments: dict) -> dict:
    tool_function = TOOL_REGISTRY.get(name)

    if tool_function is None:
        result = {
            "ok": False,
            "error": f"Calling unknow tool: {name}"
        }
    else:
        try:
            data = tool_function(**arguments)
            result = {
                "ok": True,
                "data": data
            }
            
        except Exception as e:
            result = {
                "ok": False,
                "error": str(e)
            }
    return result
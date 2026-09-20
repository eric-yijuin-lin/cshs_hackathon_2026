import json
from openai import OpenAI
from ai.agent.tools import get_device_status
from ai.agent.tool_definitions import TOOLS

client = OpenAI()

response = client.responses.create(
    model="gpt-5.5",
    input="sensor-01 現在的狀態為何？",
    tools=TOOLS
)

for item in response.output:
    if item.type == "function_call":
        arguments = json.loads(item.arguments)
        result = get_device_status(**arguments)

        response = client.responses.create(
            model="gpt-5.5",
            previous_response_id=response.id,
            input=[
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result)
                }
            ],
            tools=TOOLS
        )
        print(response.output_text)
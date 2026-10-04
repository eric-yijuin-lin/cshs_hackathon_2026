from openai import OpenAI
from ai.agent.tool_definitions import TOOLS

class LLMClient:
    def __init__(self):
        self.client = OpenAI()

    def create_response(
        self,
        input,
        tools = TOOLS,
        previous_response_id = None
    ):
        response = self.client.responses.create(
            model = "gpt-5.5",
            input = input,
            tools = tools,
            previous_response_id = previous_response_id
        )
        return response

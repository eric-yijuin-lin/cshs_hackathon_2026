from ai.agent.llm_client import LLMClient
from ai.agent.tool_definitions import TOOLS
from ai.agent.tool_executor import execute_tool
from ai.agent.agent import Agent

llm = LLMClient()

agent = Agent(
    llm_client = llm,
    tools = TOOLS,
    tool_executor = execute_tool
)

result = agent.run(
    "sensor-01 與 sensor-02 現在狀況如何？"
)

print(result)

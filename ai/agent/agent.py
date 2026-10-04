import json

## TODO:
# 目前還沒儲存 executor 的狀態，所以先不抽離，等到未來
# executor 有狀態管理需求，再把 execute_tool 抽成
# class，然後重新命名為 tool_executor
class Agent:
    def __init__(self, llm_client, tools, tool_executor):
        self.llm_client = llm_client
        self.tools = tools
        self.execute_tool = tool_executor

    def run(self, user_input):
        response = self.llm_client.create_response(
            input = user_input,
            tools = self.tools
        )

        while True:
            function_calls = [
                item 
                for item in response.output 
                if item.type == "function_call"
            ]

            if not function_calls:
                return response.output_text

            outputs = []

            for call in function_calls:
                print("[debg] calling function...")
                print(f"[debug] name: {call.name}, args: {call.arguments}")
                print(f"[debug] type of name: {type(call.name)}, type of args: {type(call.arguments)}")
                result = self.execute_tool(
                    call.name, 
                    json.loads(call.arguments))
                print(f"[debug] {result}")
                outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result)
                })

            response = self.llm_client.create_response(
                previous_response_id = response.id,
                input = outputs,
                tools = self.tools
            )

# from ..logger import get_logger
from langchain_core.tools import tool
from .ToolManager import ToolManager
from .GUIAgent.agent import ReActGUIAgent

@ToolManager.register
@tool
def callGUIAgent(prompt:str):
    """
    Args:
        prompt: 需要GUIAgent执行的操作指令，格式为自然语言描述。
    """
    agent = ReActGUIAgent()
    agent.run_task(prompt)
    return f"调用GUIAgent执行操作: {prompt}"



if __name__ == "__main__":
    print(callGUIAgent.args_schema)
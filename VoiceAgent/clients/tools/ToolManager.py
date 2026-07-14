from langchain_core.messages import ToolMessage
from logger import get_logger


class ToolManager:
    tools_list = []
    tools_map = {}
    _logger = get_logger(__name__)

    def __init__(self):
        pass

    @classmethod
    def register(cls, func):
        """
        注册工具函数
        """
        # 这里可以添加一些注册逻辑，例如将工具函数存储在一个列表或字典中
        cls.tools_list.append(func)
        cls.tools_map[func.name] = func

    def get_tools(self):
        return self.tools_list

    def call_tool(self, tool_call: dict):
        tool_msg=self.tools_map[tool_call["name"]].invoke(tool_call["args"])
        self._logger.debug(f"工具调用结果: {tool_msg}")
        return ToolMessage(content=tool_msg, tool_call_id=tool_call["id"])

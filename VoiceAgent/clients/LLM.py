from .client import Client
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from .tools.ToolManager import ToolManager
from logger import get_logger
from time import time

import json


@Client.register("LLM")
class LLM(Client):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        system_prompt: str,
        model: str,
        reasoning_effort: str = "low",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.system_prompt = system_prompt
        self.model = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            reasoning_effort=reasoning_effort,
        )
        self.reasoning_effort = reasoning_effort
        self.memory = [SystemMessage(content=system_prompt)]
        self.manager = ToolManager()
        self.tools = self.manager.get_tools()
        self.model_wtools = self.model.bind_tools(self.tools)
        self._logger = get_logger(f"{__name__}.{__class__.__name__}")
        self._logger.info(f"工具列表：{self.tools}")

    def start(self):
        pass

    def get_response(self, prompt: str) -> str:
        current_time = time()
        self.memory.append(HumanMessage(content=prompt))
        response = self.model_wtools.invoke(self.memory)
        self.memory.append(response)
        for tc in response.tool_calls:
            self.memory.append(self.manager.call_tool(tc))
        current_time = time() - current_time
        self._logger.info(f"获取响应耗时: {current_time:.2f}秒")
        self._logger.debug(f"获取响应: {response}")
        self._logger.debug(f"更新记忆: {self.memory}")
        return response

    def get_streaming_response(self, prompt: str):
        self._logger.debug(f"获取流式响应: {prompt}")
        self.memory.append(HumanMessage(content=prompt))
        for event in self.model_wtools.stream_events(self.memory, version="v3"):
            self._logger.debug(f"流式事件: {json.dumps(event, ensure_ascii=False)}")
            if event["event"] == "content-block-delta":
                if event["delta"]["type"] == "text-delta":
                    chunk = event["delta"]["text"]
                    yield chunk
                elif event["delta"]["type"] == "block-delta":
                    continue
            elif event["event"] == "content-block-finish":
                if event["content"]["type"] == "text":
                    response_text = event["content"]["text"]
                    self.memory.append(AIMessage(response_text))
                    self._logger.debug(f"更新记忆: {self.memory}")
                    self._logger.debug(f"流式响应完成: {response_text}")
                elif event["content"]["type"] == "tool_call":
                    self.memory.append(self.manager.call_tool(event["content"]))

    def stop(self):
        pass

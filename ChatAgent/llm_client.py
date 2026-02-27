from openai import OpenAI
from config import Config

class LLMClient:
    """
    负责封装大模型接口调用，与任何特定的业务逻辑分离
    """
    def __init__(self):
        # 初始化 OpenAI 兼容客户端
        self.client = OpenAI(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_API_BASE
        )
        self.model = Config.LLM_MODEL

    def chat(self, messages: list) -> str:
        """发送一组消息列表并获取回复的文本"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            content = response.choices[0].message.content
            return str(content) if content else ""
        except Exception as e:
            return f"❌ [大模型调用异常]: {e}"

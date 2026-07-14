from factory.ClientFactory import ClientFactory
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

prompt = "你是一个专业的助手，请确保你的回答简洁明了，直接解决用户的问题。"

factory = ClientFactory()

client = factory.create_client(
    "LLM",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    system_prompt=prompt,
    model="deepseek-v4-pro",
)
client.start()

for chunk in client.get_streaming_response("请帮我到浏览器中搜索bilibili"):
    print(chunk, end="", flush=True)
# print(client.get_response("北京天气怎么样？"))

# Please install OpenAI SDK first: `pip3 install openai`
import os
from openai import OpenAI
from dotenv import load_dotenv
from clone import StreamingTTS
from voice_init import init_dashscope_api_key

load_dotenv() 

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")


def streaming_chat(input:str):
    tts=StreamingTTS()
    tts.start(voice_name="shu")
    response=client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": input},
        ],
        stream=True,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}}
    )
    for chunk in response:
        content=chunk.choices[0].delta.content
        if content:
            tts.feed(content)
            print(chunk.choices[0].delta.content, end='  ')

    tts.finish()

if __name__ == "__main__":
    init_dashscope_api_key()
    # chat("What is the capital of France?")
    streaming_chat("请使用中文介绍自己")
# Please install OpenAI SDK first: `pip3 install openai`
import os
from openai import OpenAI
from dotenv import load_dotenv
from clone import StreamingTTS
from voice_init import init_dashscope_api_key
from datetime import datetime

load_dotenv() 

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")


def streaming_chat(input:str):
    start_time = datetime.now()
    tts=StreamingTTS()
    tts.start(voice_name="shu")
    client_time=datetime.now()
    print(f"Time to start the client: {(client_time - start_time).total_seconds():.2f} seconds")
    
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

    response_time=datetime.now()
    print(f"\nTime to receive the first response: {(response_time - client_time).total_seconds():.2f} seconds")
    for chunk in response:
        content=chunk.choices[0].delta.content
        if content:
            tts.feed(content)
            print(chunk.choices[0].delta.content, end='', flush=True)
    tts.feed_rest()
    # tts.finish()
    end_time = datetime.now()
    print(f"\nTotal time for streaming response: {(end_time - response_time).total_seconds():.2f} seconds")
    print(f"Total time from request to finish: {(end_time - start_time).total_seconds():.2f} seconds")

if __name__ == "__main__":
    init_dashscope_api_key()
    # chat("What is the capital of France?")
    streaming_chat("请使用中文介绍自己")
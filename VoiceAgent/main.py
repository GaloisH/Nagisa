from stt import RealtimeSTT
import sys
import pyaudio
import threading
import queue
from clone import StreamingTTS
import os
from openai import OpenAI
from dotenv import load_dotenv
from pynput import keyboard

load_dotenv()

SAMPLE_RATE = 16000  # 采样率：16kHz
CHANNELS = 1  # 单声道
SAMPLE_WIDTH = 2  # 16-bit = 2 字节/样本
CHUNK_FRAMES = 1600  # 每块帧数 = 0.1 秒
FORMAT = pyaudio.paInt16

# ─── 回调与队列 ────────────────────────────────────────────────────
audio_queue = queue.Queue()
stop_event = threading.Event()
text = ""
recording = False

if __name__ == "__main__":

    client = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
    )
    stt = RealtimeSTT()
    tts = StreamingTTS()
    recording=False

    def on_press(key):
        global recording
        if key == keyboard.Key.space:
            if recording:
                return
            recording = True
            if stt.is_paused:
                print("\n[Main进程捕获] 恢复 STT 采集")
                stt.resume()
        elif key == keyboard.Key.esc:
            print("\n[Main进程捕获] 收到退出指令")
            stop_event.set()
            return False

    def on_release(key):
        global recording
        global tts
        if key == keyboard.Key.space:
            recording = False
            print("\n[Main进程捕获] 暂停 STT 采集")
            text = stt.transcript_queue.get(timeout=30)
            stt.pause()
            print(f"\n[Main进程捕获] 获取到对应文本: {text}")
            try:
                response = client.chat.completions.create(
                    model="deepseek-v4-pro",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant"},
                        {"role": "user", "content": "请用中文介绍自己"},
                    ],
                    stream=True,
                    reasoning_effort="low",
                    extra_body={"thinking": {"type": "enabled"}},
                )
                for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        tts.feed(content)
                        print(chunk.choices[0].delta.content, end="", flush=True)
                tts.finish()
                tts=StreamingTTS()
                tts.start(voice_name="shu")

                # 🆕 等待 TTS 播放完毕，再恢复 STT
            except queue.Empty:
                pass
            except Exception as e:
                print(f"\n[Main进程捕获] API 调用出错: {e}")

    stt.start()
    tts.start(voice_name="shu")
    stt.pause()
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)

    try:
        listener.start()
        while not stop_event.is_set():
            stop_event.wait(timeout=0.5)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        listener.stop()
        stt.stop()
        tts.finish()

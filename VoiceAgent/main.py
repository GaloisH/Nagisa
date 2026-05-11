from stt import RealtimeSTT
import signal
import sys
import pyaudio
import threading
import queue
from clone import StreamingTTS
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SAMPLE_RATE   = 16000   # 采样率：16kHz
CHANNELS      = 1       # 单声道
SAMPLE_WIDTH  = 2       # 16-bit = 2 字节/样本
CHUNK_FRAMES  = 1600    # 每块帧数 = 0.1 秒
FORMAT        = pyaudio.paInt16

# ─── 回调与队列 ────────────────────────────────────────────────────
audio_queue = queue.Queue()
stop_event  = threading.Event()

if __name__ == "__main__":
    client = OpenAI(
                    api_key=os.environ.get('DEEPSEEK_API_KEY'),
                    base_url="https://api.deepseek.com")
    stt = RealtimeSTT()

    def handle_exit(sig, frame):
        stt.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT,  handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    stt.start()

    try:
        while not stop_event.is_set():
            try:
                text = stt.transcript_queue.get(timeout=0.5)
                print(f"\n[Main进程捕获] 获取到对应文本: {text}")

                # 🆕 暂停 STT 采集，防止 TTS 输出被麦克风捕获
                stt.pause()

                # 每轮重建 TTS（finish 后 session 结束）
                tts = StreamingTTS()
                tts.start(voice_name="kaltsit1")

                response = client.chat.completions.create(
                    model="deepseek-v4-pro",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant"},
                        {"role": "user", "content": text},
                    ],
                    stream=True,
                    reasoning_effort="low",
                    extra_body={"thinking": {"type": "enabled"}}
                )
                for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        tts.feed(content)
                        print(chunk.choices[0].delta.content, end='', flush=True)

                # 🆕 等待 TTS 播放完毕，再恢复 STT
                tts.finish()
                stt.resume()
            except queue.Empty:
                continue
    except KeyboardInterrupt:
        stt.stop()
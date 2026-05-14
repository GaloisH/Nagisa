# coding=utf-8
# Installation instructions for pyaudio:
# APPLE Mac OS X
#   brew install portaudio
#   pip install pyaudio
# Debian/Ubuntu
#   sudo apt-get install python-pyaudio python3-pyaudio
#   or
#   pip install pyaudio
# CentOS
#   sudo yum install -y portaudio portaudio-devel && pip install pyaudio
# Microsoft Windows
#   python -m pip install pyaudio

import pyaudio
import os
import requests
import base64
import pathlib
import threading
import time
import dashscope
from dashscope.audio.qwen_tts_realtime import QwenTtsRealtime, QwenTtsRealtimeCallback, AudioFormat
import json
from dotenv import load_dotenv
# ======= 常量配置 =======
load_dotenv()
BASE_DIR= os.path.dirname(os.path.abspath(__file__))
DEFAULT_TARGET_MODEL = "qwen3-tts-vc-realtime-2026-01-15" 
VOICE_NAME="shu"
TEXT_TO_SYNTHESIZE = [
    '对吧~我就特别喜欢这种超市，',
    '尤其是过年的时候',
    '去逛超市',
    '就会觉得',
    '超级超级开心！',
    '想买好多好多的东西呢！'
]

def init_dashscope_api_key():
    """
    初始化 dashscope SDK 的 API key
    """
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# ======= 回调类 =======
class MyCallback(QwenTtsRealtimeCallback):
    """
    自定义 TTS 流式回调
    """
    def __init__(self):
        self.complete_event = threading.Event()
        self._player = pyaudio.PyAudio()
        self._stream = self._player.open(
            format=pyaudio.paInt16, channels=1, rate=24000, output=True
        )
        self.tts = None

    def on_open(self) -> None:
        print('[TTS] 连接已建立')

    def on_close(self, close_status_code, close_msg) -> None:
        self._stream.stop_stream()
        self._stream.close()
        self._player.terminate()
        print(f'[TTS] 连接关闭 code={close_status_code}, msg={close_msg}')

    def on_event(self, response: dict) -> None:
        try:
            event_type = response.get('type', '')
            if event_type == 'session.created':
                print(f'[TTS] 会话开始: {response["session"]["id"]}')
            elif event_type == 'response.audio.delta':
                audio_data = base64.b64decode(response['delta'])
                self._stream.write(audio_data)
            elif event_type == 'response.done':
                print(f'[TTS] 响应完成, Response ID: {self.tts.get_last_response_id()}')
            elif event_type == 'session.finished':
                print('[TTS] 会话结束')
                self.complete_event.set()
        except Exception as e:
            print(f'[Error] 处理回调事件异常: {e}')

    def wait_for_finished(self):
        self.complete_event.wait()

class StreamingTTS():
    def __init__(self,model=DEFAULT_TARGET_MODEL, url='wss://dashscope.aliyuncs.com/api-ws/v1/realtime'):
        self.callback = MyCallback()
        self.tts = QwenTtsRealtime(
            model=model,
            callback=self.callback,
            url=url
        )
        self.callback.tts = self.tts
        self.buffer=""
        self.ending={",",".","!","?","\n","，","。","！","？"}

    def start(self, voice_name=VOICE_NAME):
        init_dashscope_api_key()
        with open(os.path.join(BASE_DIR, "config.json"), "r") as f:
            config = json.load(f)
        voice_token=config[voice_name]["voice"]["voice_id"]
        self.tts.connect()
        self.tts.update_session(
            voice=voice_token,
            response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            mode='server_commit',
            speech_rate=1
        )

    def feed(self,text_chunk):
        self.buffer+=text_chunk
        if self.buffer and self.buffer[-1] in self.ending:
            self.tts.append_text(self.buffer)
            self.buffer=""

    def feed_rest(self):
        if self.buffer.strip():
            self.tts.append_text(self.buffer)
            self.buffer=""
        self.callback.wait_for_finished()
        # self.callback.wait_for_finished()

    def finish(self):
        if self.buffer.strip():
            self.tts.append_text(self.buffer)
            self.buffer=""
        self.tts.finish()
        self.callback.wait_for_finished()

# ======= 主入口 =======
if __name__ == '__main__':
    tts = StreamingTTS()
    tts.start()
    for text in TEXT_TO_SYNTHESIZE:
        tts.feed(text)
        time.sleep(0.5)  # 模拟文本逐渐输入的效果

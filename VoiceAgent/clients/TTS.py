import pyaudio
import os
import base64
import threading
import dashscope
from dashscope.audio.qwen_tts_realtime import (
    QwenTtsRealtime,
    QwenTtsRealtimeCallback,
    AudioFormat,
)
import json
from dotenv import load_dotenv
from .client import Client
import queue
from logger import get_logger

BASE_DIR = "VoiceAgent"


def init_dashscope_api_key():
    """
    初始化API key
    """
    env_path = os.path.join(BASE_DIR, ".env")
    load_dotenv(env_path)
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")


class TTSCallback(QwenTtsRealtimeCallback):
    """
    TTS流式回调
    """

    def __init__(self):
        self.complete_event = threading.Event()
        self._player = pyaudio.PyAudio()
        self._stream = self._player.open(
            format=pyaudio.paInt16, channels=1, rate=24000, output=True
        )
        self.tts = None
        self._logger = get_logger(f"{__name__}.{__class__.__name__}")

    def on_open(self) -> None:
        self._logger.info("连接已建立")

    def on_close(self, close_status_code, close_msg) -> None:
        self._stream.stop_stream()
        self._stream.close()
        self._player.terminate()
        self._logger.info(f"连接关闭 code={close_status_code}, msg={close_msg}")

    def on_event(self, response: dict) -> None:
        try:
            event_type = response.get("type", "")
            if event_type == "session.created":

                self._logger.info(f'会话开始: {response["session"]["id"]}')
            elif event_type == "response.audio.delta":
                audio_data = base64.b64decode(response["delta"])
                self._stream.write(audio_data)
            elif event_type == "response.done":
                self._logger.info(
                    f"响应完成, Response ID: {self.tts.get_last_response_id()}"
                )
            elif event_type == "session.finished":
                self._logger.info("会话结束")
                self.complete_event.set()
        except Exception as e:
            self._logger.exception(f"TTS回调处理异常")

    def wait_for_finished(self):
        self.complete_event.wait()


@Client.register("TTS")
class TTS(Client):
    def __init__(
        self,
        model="qwen3-tts-vc-realtime-2026-01-15",
        url="wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
    ):
        init_dashscope_api_key()
        self.callback = TTSCallback()
        self.tts = QwenTtsRealtime(model=model, callback=self.callback, url=url)
        self.callback.tts = self.tts
        self.buffer = ""
        self.ending = {",", ".", "!", "?", "\n", "，", "。", "！", "？"}
        self.chunk_queue = queue.Queue()
        self.buffer_lock = threading.Lock()

    def start(self, voice_name="shu"):
        with open(os.path.join(BASE_DIR, "config.json"), "r") as f:
            config = json.load(f)
        voice_token = config[voice_name]["voice"]["voice_id"]

        self.tts.connect()
        self.tts.update_session(
            voice=voice_token,
            response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            mode="commit",
            speech_rate=1,
        )

    def feed(self, text_chunk):
        """
        接收文本输入，按标点分块提交。
        """
        self.buffer += text_chunk

        if self.buffer and self.buffer[-1] in self.ending:
            self.chunk_queue.put(self.buffer)
            self.buffer = ""

    def feed_rest(self):
        """
        提交剩余未结尾的文本。
        """
        if self.buffer.strip():
            self.chunk_queue.put(self.buffer)
            self.buffer = ""

    def stop(self):
        """
        停止TTS会话，等待完成。
        """
        if self.buffer.strip():
            self.chunk_queue.put(self.buffer)
            self.buffer = ""

        self.tts.finish()
        self.callback.wait_for_finished()

    def finish(self):
        """
        提交剩余文本并结束会话。
        """
        if self.buffer.strip():
            self.chunk_queue.put(self.buffer)
            self.buffer = ""

        self.tts.finish()
        self.callback.wait_for_finished()

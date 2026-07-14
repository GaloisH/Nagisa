import pyaudio
import queue
import threading
import base64
import os
import dashscope
from dashscope.audio.qwen_omni import *
from dashscope.audio.qwen_omni.omni_realtime import TranscriptionParams
from dotenv import load_dotenv
from .client import Client
from logger import get_logger

BASE_DIR = os.getcwd()
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ─── ASR 回调 ──────────────────────────────────────────────────────
class RealtimeCallback(OmniRealtimeCallback):
    def __init__(self, transcript_queue, stop_event):
        self.transcript_queue = transcript_queue
        self.stop_event = stop_event
        self._logger = get_logger(f"{__name__}.{__class__.__name__}")

    def on_open(self):
        self._logger.info("连接已建立")

    def on_close(self, code, msg):
        self._logger.info(f"连接已关闭 code={code} msg={msg}")
        self.stop_event.set()

    def on_event(self, response):
        t = response.get("type", "")
        if t == "session.created":
            self._logger.info(f"会话已创建: {response['session']['id']}")
        elif t == "input_audio_buffer.speech_started":
            self._logger.info("🎙  说话开始...")
        elif t == "input_audio_buffer.speech_stopped":
            self._logger.info("🔇 说话结束")
        elif t == "conversation.item.input_audio_transcription.text":
            # 中间结果（边说边出）
            text = response["text"] + response.get("stash", "")
            print(f"\r  ▶ {text}", end="", flush=True)
        elif t == "conversation.item.input_audio_transcription.completed":
            # 最终结果（句末确认）
            self._logger.info(f"\n最终: {response['transcript']}")
            self.transcript_queue.put(response["transcript"])



# ─── STT 类封装 ──────────────────────────────────────────────────
@Client.register("STT")
class STT(Client):
    def __init__(self, api_key=None, model="qwen3-asr-flash-realtime"):
        dashscope.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", "YOUR_KEY")
        self.model = model
        self.audio_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.transcript_queue = queue.Queue()
        self.callback = RealtimeCallback(self.transcript_queue, self.stop_event)
        self.is_paused = False
        self.conversation = None
        self.pa = None
        self.stream = None
        self.sender = None
        self._logger = get_logger(f"{__name__}.{__class__.__name__}")
        self.config = {
            "SAMPLE_RATE": 16000,
            "CHANNELS": 1,
            "SAMPLE_WIDTH": 2,
            "CHUNK_FRAMES": 1600,
            "FORMAT": pyaudio.paInt16
        }

    def audio_callback(self,in_data, frame_count, time_info, status):
        """
        PyAudio 在独立音频线程中调用此函数。
        只做一件事：把原始 PCM 数据推入队列，绝不阻塞。
        """
        if status:
            print(f"[Audio status] {status}")
        self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)
    
    def send_loop(self,conversation):
        """
        独立线程，持续从队列取数据并发送。
        与音频回调解耦，避免阻塞采集。
        """
        while not self.stop_event.is_set():
            try:
                # 最多等 0.5 秒，避免永久阻塞
                chunk = self.audio_queue.get(timeout=0.5)
                audio_b64 = base64.b64encode(chunk).decode("ascii")
                conversation.append_audio(audio_b64)
            except queue.Empty:
                continue
            except Exception as e:
                self._logger.exception(f"发送音频数据异常")
                print(f"[Send error] {e}")
                break

    def start(self):
        """
        建立 WebSocket 连接，启动 ASR 会话。
        """
        self.conversation = OmniRealtimeConversation(
            model=self.model,
            url="wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
            callback=self.callback,
        )
        self.conversation.connect()
        self.conversation.update_session(
            output_modalities=[MultiModality.TEXT],
            enable_input_audio_transcription=True,
            transcription_params=TranscriptionParams(
                language="zh",
                sample_rate=self.config["SAMPLE_RATE"],
                input_audio_format="pcm",
            ),
        )

        # 2. 启动 PyAudio 采集流
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format=self.config["FORMAT"],
            channels=self.config["CHANNELS"],
            rate=self.config["SAMPLE_RATE"],
            input=True,
            frames_per_buffer=self.config["CHUNK_FRAMES"],
            stream_callback=self.audio_callback,
        )
        self.stream.start_stream()
        self._logger.info("🎤 开始录音...\n")

        # 3. 启动发送线程
        self.sender = threading.Thread(
            target=self.send_loop, args=(self.conversation,), daemon=True
        )
        self.sender.start()

    def pause(self):
        """暂停麦克风采集，清空队列，保持 WebSocket 连接"""
        self.is_paused = True
        if self.stream and self.stream.is_active():
            self.stream.stop_stream()
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

    def resume(self):
        """恢复麦克风采集"""
        self.is_paused = False
        if self.stream and not self.stream.is_active():
            self.stream.start_stream()

    def stop(self):
        self._logger.info("\n正在停止...")
        self.stop_event.set()

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.pa:
            self.pa.terminate()
        if self.sender:
            self.sender.join(timeout=2)
        if self.conversation:
            self.conversation.end_session()
            self.conversation.close()
        self._logger.info("已退出。")

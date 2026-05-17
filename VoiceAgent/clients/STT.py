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

BASE_DIR=os.getcwd()
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ─── 音频参数（必须与 ASR 服务端匹配）─────────────────────────────
SAMPLE_RATE   = 16000   # 采样率：16kHz
CHANNELS      = 1       # 单声道
SAMPLE_WIDTH  = 2       # 16-bit = 2 字节/样本
CHUNK_FRAMES  = 1600    # 每块帧数 = 0.1 秒
FORMAT        = pyaudio.paInt16

# ─── 回调与队列 ────────────────────────────────────────────────────
audio_queue = queue.Queue()
stop_event  = threading.Event()

def audio_callback(in_data, frame_count, time_info, status):
    """
    PyAudio 在独立音频线程中调用此函数。
    只做一件事：把原始 PCM 数据推入队列，绝不阻塞。
    """
    if status:
        print(f"[Audio status] {status}")
    audio_queue.put(in_data)
    return (None, pyaudio.paContinue)

# ─── ASR 回调 ──────────────────────────────────────────────────────
class RealtimeCallback(OmniRealtimeCallback):
    def __init__(self, transcript_queue):
        self.transcript_queue = transcript_queue

    def on_open(self):
        print("✓ WebSocket 连接已建立")

    def on_close(self, code, msg):
        print(f"✗ 连接关闭 code={code} msg={msg}")
        stop_event.set()

    def on_event(self, response):
        t = response.get("type", "")
        if t == "session.created":
            print(f"  会话已创建: {response['session']['id']}")
        elif t == "input_audio_buffer.speech_started":
            print("  🎙  说话开始...")
        elif t == "input_audio_buffer.speech_stopped":
            print("  🔇 说话结束")
        elif t == "conversation.item.input_audio_transcription.text":
            # 中间结果（边说边出）
            text = response["text"] + response.get("stash", "")
            print(f"\r  ▶ {text}", end="", flush=True)
        elif t == "conversation.item.input_audio_transcription.completed":
            # 最终结果（句末确认）
            print(f"\n  ✓ 最终: {response['transcript']}")
            self.transcript_queue.put(response['transcript'])

# ─── 发送线程：队列 → Base64 → WebSocket ──────────────────────────
def send_loop(conversation):
    """
    独立线程，持续从队列取数据并发送。
    与音频回调解耦，避免阻塞采集。
    """
    while not stop_event.is_set():
        try:
            # 最多等 0.5 秒，避免永久阻塞
            chunk = audio_queue.get(timeout=0.5)
            audio_b64 = base64.b64encode(chunk).decode("ascii")
            conversation.append_audio(audio_b64)
        except queue.Empty:
            continue
        except Exception as e:
            print(f"[Send error] {e}")
            break

# ─── STT 类封装 ──────────────────────────────────────────────────
@Client.register("STT")
class STT:
    def __init__(self, api_key=None, model="qwen3-asr-flash-realtime"):
        dashscope.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", "YOUR_KEY")
        self.model = model
        self.transcript_queue = queue.Queue()
        self.callback = RealtimeCallback(self.transcript_queue)
        self.is_paused = False
        self.conversation = None
        self.pa = None
        self.stream = None
        self.sender = None

    def start(self):
        # 1. 初始化 ASR 会话
        self.conversation = OmniRealtimeConversation(
            model    = self.model,
            url      = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
            callback = self.callback,
        )
        self.conversation.connect()
        self.conversation.update_session(
            output_modalities              = [MultiModality.TEXT],
            enable_input_audio_transcription = True,
            transcription_params           = TranscriptionParams(
                language          = "zh",
                sample_rate       = SAMPLE_RATE,
                input_audio_format= "pcm",
            ),
        )

        # 2. 启动 PyAudio 采集流
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            format               = FORMAT,
            channels             = CHANNELS,
            rate                 = SAMPLE_RATE,
            input                = True,
            frames_per_buffer    = CHUNK_FRAMES,
            stream_callback      = audio_callback,
        )
        self.stream.start_stream()
        print("🎤 开始录音，按 Ctrl+C 停止...\n")

        # 3. 启动发送线程
        self.sender = threading.Thread(target=send_loop, args=(self.conversation,), daemon=True)
        self.sender.start()

    def pause(self):
        """暂停麦克风采集，清空队列，保持 WebSocket 连接"""
        self.is_paused = True
        if self.stream and self.stream.is_active():
            self.stream.stop_stream()
        while not audio_queue.empty():
            try:
                audio_queue.get_nowait()
            except queue.Empty:
                break

    def resume(self):
        """恢复麦克风采集"""
        self.is_paused = False
        if self.stream and not self.stream.is_active():
            self.stream.start_stream()

    def stop(self):
        print("\n正在停止...")
        stop_event.set()
        
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
        print("已退出。")


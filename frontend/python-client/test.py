import pyaudio
import queue
import threading
import base64
import time
import signal
import sys
import os
import dashscope
from dashscope.audio.qwen_omni import *
from dashscope.audio.qwen_omni.omni_realtime import TranscriptionParams  
from dotenv import load_dotenv
from pynput import keyboard

load_dotenv()

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
            print("\n  🎙  说话开始...")
        elif t == "input_audio_buffer.speech_stopped":
            print("\n  🔇 说话结束")
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

# todo 识别语音结束间隔稍微快了一点
# ─── STT 类封装 ──────────────────────────────────────────────────
class RealtimeSTT:
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

    # 一共三个线程，与云端的websocket连接的回调执行线程，PyAudio的stream音频采集回调执行线程，以及在wss连接上发送音频给云端的发送线程
    # 工作流程为，麦克风stream流每0.1秒采集一次音频数据并触发回调，回调函数audio_callback将采集到的PCM原始音频数据放入audio_queue队列中；
    # 发送线程send_loop不断从audio_queue队列中取出音频数据，进行Base64编码后通过WebSocket连接发送给云端；
    # 云端处理后将转录结果通过WebSocket的回调函数on_event返回，由wss连接的回调线程执行，最终将转录结果放入transcript_queue队列中，主线程不断从transcript_queue队列中取出转录结果进行打印或其他处理。
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
            turn_detection_silence_duration_ms = 1200,# VAD断句检测阈值（ms）。静音持续时长超过该阈值将被认为是语句结束。这里相比默认800调高了一点
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



# ─── 键盘控制器 ────────────────────────────────────────────────────────────────
class KeyboardController:
    """监听 Space（PTT 录音）和 Esc（退出），回调保持轻量不阻塞。"""

    def __init__(self, stt, stop_event: threading.Event):
        self._stt        = stt
        self._stop_event = stop_event
        self._recording  = False
        self._listener   = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )

    def start(self):
        self._listener.start()

    def stop(self):
        self._listener.stop()

    def _on_press(self, key):
        if key == keyboard.Key.space:
            if self._recording:
                return
            self._recording = True
            if self._stt.is_paused:
                print("\n[键盘线程] 恢复 STT 采集")
                self._stt.resume()
        elif key == keyboard.Key.esc:
            print("\n[键盘线程] 收到退出指令")
            self._stop_event.set()
            return False

    def _on_release(self, key):
        if key == keyboard.Key.space:
            self._recording = False
            print("\n[键盘线程] 暂停 STT 采集")
            self._stt.pause()
            try:
                text = self._stt.transcript_queue.get_nowait()
                print(f"\n[键盘线程] 文本入队: {text}")
            except queue.Empty:
                print("\n[键盘线程] 暂无识别结果，跳过")


def main():
    stop_event = threading.Event()
    stt = RealtimeSTT()
    keyboard_ctrl = KeyboardController(stt, stop_event)
    stt.start()
    stt.pause()
    keyboard_ctrl.start()

    try:
        while not stop_event.is_set():
            stop_event.wait(timeout=0.5)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        keyboard_ctrl.stop()
        stt.stop()

if __name__ == "__main__":
    main()
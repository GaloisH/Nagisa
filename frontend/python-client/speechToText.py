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


load_dotenv()

# ─── 音频参数（必须与 ASR 服务端匹配）─────────────────────────────
SAMPLE_RATE   = 16000   # 采样率：16kHz
CHANNELS      = 1       # 单声道
SAMPLE_WIDTH  = 2       # 16-bit = 2 字节/样本
CHUNK_FRAMES  = 1600    # 每块帧数 = 0.1 秒
FORMAT        = pyaudio.paInt16

# ─── 回调与队列 ────────────────────────────────────────────────────

stop_event  = threading.Event()

# ─── ASR 回调 ──────────────────────────────────────────────────────
class RealtimeCallback(OmniRealtimeCallback):
    def __init__(self, transcript_queue, text_callback=None, completed_event=None):
        self.transcript_queue = transcript_queue
        self.text_callback = text_callback
        # 手动commit模式completed回调触发标识
        self.completed_event = completed_event

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
            if self.text_callback:
                self.text_callback(text)
            print(f"\r  ▶ {text}", end="", flush=True)
        elif t == "conversation.item.input_audio_transcription.completed":
            # 最终结果（句末确认）
            if self.text_callback:
                self.text_callback(response['transcript'])
            print(f"\n  ✓ 最终: {response['transcript']}")
            self.transcript_queue.put(response['transcript'])
            if self.completed_event:
                self.completed_event.set()  # 唤醒等待的线程，如 keyboard listener



# todo 识别语音结束间隔稍微快了一点
# ─── STT 类封装 ──────────────────────────────────────────────────
class RealtimeSTT:
    def __init__(self, api_key=None, model="qwen3-asr-flash-realtime", text_callback=None):
        dashscope.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", "YOUR_KEY")
        self.model = model
        self.transcript_queue = queue.Queue()
        self.completed_event = threading.Event()
        self.callback = RealtimeCallback(self.transcript_queue, text_callback=text_callback, completed_event=self.completed_event)
        self.is_paused = False
        self.conversation = None
        self.pa = None
        self.stream = None
        self.sender = None
        self.audio_queue = queue.Queue()
        

    def audio_callback(self,in_data, frame_count, time_info, status):
        """
        PyAudio 在独立音频线程中调用此函数。
        只做一件事：把原始 PCM 数据推入队列，绝不阻塞。
        """
        if status:
            print(f"[Audio status] {status}")
        self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)
    
    # ─── 发送线程：队列 → Base64 → WebSocket ──────────────────────────
    def send_loop(self):
        """
        独立线程，持续从队列取数据并发送。
        与音频回调解耦，避免阻塞采集。
        """
        while not stop_event.is_set():
            try:
                # 最多等 0.5 秒，避免永久阻塞
                chunk = self.audio_queue.get(timeout=0.5)
                audio_b64 = base64.b64encode(chunk).decode("ascii")
                self.conversation.append_audio(audio_b64)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Send error] {e}")
                break

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
            enable_turn_detection=False, # commit 模式
            # turn_detection_silence_duration_ms = 1200,# VAD断句检测阈值（ms）。静音持续时长超过该阈值将被认为是语句结束。这里相比默认800调高了一点
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
            stream_callback      = self.audio_callback,
        )
        self.stream.start_stream()
        print("🎤 开始录音，按 Ctrl+C 停止...\n")

        # 3. 启动发送线程
        self.sender = threading.Thread(target=self.send_loop, daemon=True)
        self.sender.start()

    def pause(self):
        """暂停麦克风采集并设置标识"""
        self.is_paused = True
        if self.stream and self.stream.is_active():
            self.stream.stop_stream()

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






def main():
    stop_event = threading.Event()



if __name__ == "__main__":
    main()
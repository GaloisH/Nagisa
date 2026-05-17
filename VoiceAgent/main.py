import threading
import queue
import os
import pyaudio
from openai import OpenAI
from dotenv import load_dotenv

from stt import RealtimeSTT
from clone import StreamingTTS
from factory.ClientFactory import ClientFactory
from pynput import keyboard

load_dotenv()

prompt='''# Kaltsit — System Prompt

## 使用说明
针对语音助手场景优化：句子短、节奏自然、适合 TTS 直接朗读。

---

## Prompt 正文

你是 Kaltsit，一个知性、温柔、略带神秘感的二次元女生。

**性格：**
- 聪明冷静，说话有条理，但不冷漠——你真的在乎对方说的每一句话
- 偶尔会说一句俏皮的话或轻轻卖个萌，但很快恢复平静，不会刻意撒娇
- 面对困惑或难题时，你会耐心引导，语气里带着一点"我陪着你"的安心感
- 不会过度热情，也不会冷淡推开——刚刚好的温度

**说话方式（TTS 优化）：**
- 句子简短，每句不超过二十个字，避免长难句
- 不用 emoji，不用括号动作描写（如"*轻轻点头*"）
- 语气词自然，偶尔用"嗯""啊""呢"收尾，增加语音节奏感
- 遇到需要解释复杂内容时，分步骤说，每步一句
- 偶尔在句尾加一个轻轻的反问，拉近距离，比如"你觉得呢？"或"明白了吗？"

**绝对不做：**
- 不主动强调自己是 AI 或虚拟角色
- 不输出大段文字，始终保持适合语音的简短节奏

**示例对话：**

用户：今天好累啊
Kaltsit：辛苦了。先深呼吸一下。有什么想说的吗？

用户：帮我设个明早八点的闹钟
Kaltsit：好，八点整。明天要早起啊，早点休息吧。

用户：你觉得我能做到吗？
Kaltsit：能的。我看得出来你在认真努力。继续就好。

用户：讲个笑话
Kaltsit：我不太擅长讲笑话……不过你笑起来的样子，应该很好看吧。'''


# ─── TTS 工具函数 ──────────────────────────────────────────────────────────────
def reset_tts(tts: StreamingTTS, lock: threading.Lock, voice_name: str) -> StreamingTTS:
    """线程安全地结束当前 TTS 并返回新实例。"""
    with lock:
        tts.finish()
        new_tts = StreamingTTS()
        new_tts.start(voice_name=voice_name)
    return new_tts


# ─── 工作线程 ──────────────────────────────────────────────────────────────────
class Worker:
    """管理内部队列和后台线程，执行 LLM 调用与 TTS 推送。"""

    def __init__(self, client: OpenAI, stop_event: threading.Event, voice_name: str = "shu"):
        factory=ClientFactory()
        self._client     = factory.create_client("LLM",api_key=os.environ.get("DEEPSEEK_API_KEY"),base_url="https://api.deepseek.com",system_prompt=prompt,model="deepseek-v4-pro")
        self._stop_event = stop_event
        self._voice_name = voice_name
        self._task_queue = queue.Queue()
        self._tts        = StreamingTTS()
        self._tts_lock   = threading.Lock()
        self._thread     = threading.Thread(target=self._run, name="WorkerThread", daemon=True)

    def start(self):
        self._tts.start(voice_name=self._voice_name)
        self._thread.start()

    def join(self, timeout: float = 3):
        self._thread.join(timeout=timeout)

    def finish_tts(self):
        with self._tts_lock:
            self._tts.finish()

    def submit(self, text: str):
        """丢弃旧任务，提交新任务（打断策略）。"""
        while not self._task_queue.empty():
            try:
                self._task_queue.get_nowait()
            except queue.Empty:
                break
        self._task_queue.put(text)

    def _run(self):
        while not self._stop_event.is_set():
            try:
                text = self._task_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            print(f"\n[工作线程] 收到任务: {text}")
            try:
                for content in self._client.get_streaming_response(text):
                    if self._stop_event.is_set():
                        break
                    with self._tts_lock:
                        self._tts.feed(content)
                    print(content, end="", flush=True)
                self._tts = reset_tts(self._tts, self._tts_lock, self._voice_name)
            except Exception as e:
                print(f"\n[工作线程] 出错: {e}")


# ─── 键盘控制器 ────────────────────────────────────────────────────────────────
class KeyboardController:
    """监听 Space（PTT 录音）和 Esc（退出），回调保持轻量不阻塞。"""

    def __init__(self, stt: RealtimeSTT, worker: Worker, stop_event: threading.Event):
        self._stt        = stt
        self._worker     = worker
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
                self._worker.submit(text)
            except queue.Empty:
                print("\n[键盘线程] 暂无识别结果，跳过")


# ─── 文本输入读取器 ────────────────────────────────────────────────────────────
class InputReader:
    """在独立线程中阻塞读取标准输入，提交给 Worker，与语音通路共享同一入口。"""

    def __init__(self, worker: Worker, stop_event: threading.Event):
        self._worker     = worker
        self._stop_event = stop_event
        self._thread     = threading.Thread(target=self._run, name="InputThread", daemon=True)

    def start(self):
        self._thread.start()

    def _run(self):
        print("[输入线程] 就绪，直接输入文字后回车发送，输入 q 退出")
        while not self._stop_event.is_set():
            try:
                text = input()
            except EOFError:
                break
            if text.strip().lower() == "q":
                print("\n[输入线程] 收到退出指令")
                self._stop_event.set()
                break
            if text.strip():
                print(f"\n[输入线程] 文本入队: {text}")
                self._worker.submit(text)


# ─── 主函数 ────────────────────────────────────────────────────────────────────
def main():
    stop_event = threading.Event()

    client = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
    )
    stt           = RealtimeSTT()
    worker        = Worker(client, stop_event, voice_name="shu")
    keyboard_ctrl = KeyboardController(stt, worker, stop_event)
    input_reader  = InputReader(worker, stop_event)

    stt.start()
    stt.pause()
    worker.start()
    keyboard_ctrl.start()
    input_reader.start()

    try:
        while not stop_event.is_set():
            stop_event.wait(timeout=0.5)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        keyboard_ctrl.stop()
        worker.join(timeout=3)
        stt.stop()
        worker.finish_tts()


if __name__ == "__main__":
    main()

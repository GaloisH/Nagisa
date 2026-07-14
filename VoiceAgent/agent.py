import threading
import queue
import os
from factory.ClientFactory import ClientFactory
from logger import get_logger

prompt = """
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
Kaltsit：我不太擅长讲笑话……不过你笑起来的样子，应该很好看吧。"""

class Agent:
    '''
    核心 Agent 类，负责协调 LLM、STT、TTS 客户端，处理业务逻辑，并通过回调与 GUI 通信。
    '''

    def __init__(self):
        self.state_cb = None
        self.transcript_cb = None
        self.chunk_cb = None
        self.done_cb = None
        self.error_cb = None

        self._stop_event = threading.Event()
        self._voice_name = "shu"
        self._is_paused = True

        self._client = None
        self._stt = None
        self._tts = None
        self._tts_lock = threading.Lock()
        self._task_queue = queue.Queue()
        self._worker_thread = None
        self.client_factory = ClientFactory()
        self._logger = get_logger(__name__)

    def start(self, voice_name: str = "shu") -> None:
        '''
        启动 Agent，初始化客户端并启动后台线程。'''
        self._voice_name = voice_name
        self._stop_event.clear()

        self._client = self.client_factory.create_client(
            "LLM",
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
            system_prompt=prompt,
            model="deepseek-v4-pro",
        )
        self._client.start()

        self._stt = self.client_factory.create_client(
            "STT", api_key=os.environ.get("DASHSCOPE_API_KEY")
        )
        self._stt.start()
        self._stt.pause()
        self._is_paused = True

        self._tts = self.client_factory.create_client("TTS")
        self._tts.start(voice_name=voice_name)

        self._worker_thread = threading.Thread(
            target=self._run, name="AgentWorker", daemon=True
        )
        self._worker_thread.start()

    def stop(self) -> None:
        '''
        安全停止 Agent，结束后台线程并清理资源。
        '''
        self._stop_event.set()
        
        if self._worker_thread:
            self._worker_thread.join(timeout=3)
        if self._tts:
            with self._tts_lock:
                self._tts.finish()

    def submit_text(self, text: str) -> None:
        
        while not self._task_queue.empty():
            try:
                self._task_queue.get_nowait()
            except queue.Empty:
                break
        self._task_queue.put(text)

    def start_listening(self) -> None:
        if self._stt and self._is_paused:
            self._stt.resume()
            self._is_paused = False
        if self.state_cb:
            self.state_cb("idle", "listening")

    def stop_listening(self) -> None:
        if self._stt and not self._is_paused:
            self._stt.pause()
            self._is_paused = True
        if self.state_cb:
            self.state_cb("listening", "idle")
        try:
            text = self._stt.transcript_queue.get_nowait()
            if self.transcript_cb:
                self.transcript_cb(text)
            self.submit_text(text)
        except queue.Empty:
            pass

    # ── 回调注册 ──────────────────────────────────────────────────────────

    def on_state_change(self, cb):
        self.state_cb = cb

    def on_transcript(self, cb):
        self.transcript_cb = cb

    def on_response_chunk(self, cb):
        self.chunk_cb = cb

    def on_response_done(self, cb):
        self.done_cb = cb

    def on_error(self, cb):
        self.error_cb = cb

    def _run(self):
        while not self._stop_event.is_set():
            try:
                text = self._task_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            self._logger.info(f"收到任务: {text}")

            if self.state_cb:
                self.state_cb("idle", "thinking")

            try:
                full_response = ""
                self._logger.debug(f"发送到 LLM: {text}")
                for chunk in self._client.get_streaming_response(text):
                    if self._stop_event.is_set():
                        break
                    delta = chunk
                    if delta:
                        full_response += delta
                        if self.chunk_cb:
                            self.chunk_cb(delta)
                        with self._tts_lock:
                            self._tts.feed(delta)
                        print(delta, end="", flush=True)
                print()

                if not self._stop_event.is_set():
                    with self._tts_lock:
                        self._tts.finish()
                        self._tts = self.client_factory.create_client("TTS")
                        self._tts.start(voice_name=self._voice_name)

                if self.done_cb:
                    self.done_cb(full_response)
                if self.state_cb:
                    self.state_cb("thinking", "idle")

            except Exception as e:
                self._logger.error(f"出错: {e}")
                if self.error_cb:
                    self.error_cb(str(e))
                if self.state_cb:
                    self.state_cb("thinking", "idle")

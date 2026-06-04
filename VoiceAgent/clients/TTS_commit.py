import pyaudio
import os
import base64
import threading
import dashscope
from dashscope.audio.qwen_tts_realtime import QwenTtsRealtime, QwenTtsRealtimeCallback, AudioFormat
import json
from dotenv import load_dotenv
from clients.client import Client
import queue


BASE_DIR='VoiceAgent'
_busy = False   # 补上全局变量定义


def init_dashscope_api_key():
    """
    初始化 dashscope SDK 的 API key
    """
    env_path=os.path.join(BASE_DIR,"VoiceAgent/.env")
    load_dotenv(env_path)
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# ======= 回调类 =======
class MyCallback(QwenTtsRealtimeCallback):
    def __init__(self):
        super().__init__()
        self.response_counter = 0
        self.complete_event = threading.Event()
        self.file = open(f'result_{self.response_counter}_24k.pcm', 'wb')

    def reset_event(self):
        if not self.file.closed:
            self.file.close()
        self.response_counter += 1
        self.file = open(f'result_{self.response_counter}_24k.pcm', 'wb')
        self.complete_event = threading.Event()

    def on_open(self) -> None:
        print('connection opened, init player')

    def on_close(self, close_status_code, close_msg) -> None:
        print('connection closed with code: {}, msg: {}, destroy player'.format(close_status_code, close_msg))

    def on_event(self, response: str) -> None:
        try:
            type = response['type']
            if 'session.created' == type:
                print('start session: {}'.format(response['session']['id']))
            if 'response.audio.delta' == type:
                recv_audio_b64 = response['delta']
                self.file.write(base64.b64decode(recv_audio_b64))
            if 'response.done' == type:
                print(f'response {self.tts.get_last_response_id()} done')
                global _busy
                _busy = False
                self.complete_event.set()
                self.file.close()
            if 'session.finished' == type:
                print('session finished')
                self.complete_event.set()
        except Exception as e:
            print('[Error] {}'.format(e))
            return

    def wait_for_response_done(self):
        self.complete_event.wait()

@Client.register("TTS_commit")
class TTS_COMMIT(Client):
    def __init__(self,model="qwen3-tts-vc-realtime-2026-01-15" , url='wss://dashscope.aliyuncs.com/api-ws/v1/realtime'):
        global _busy
        global tts
        init_dashscope_api_key()
        self.callback = MyCallback()
        self.tts = QwenTtsRealtime(
            model=model,
            callback=self.callback,
            url=url
        )
        self.callback.tts = self.tts
        self.buffer=""
        self.ending={",",".","!","?","\n","，","。","！","？"}
        self.chunk_queue=queue.Queue()
        _busy=False
        self.commit_thread=threading.Thread(target=self.commit_loop)

    def commit_loop(self):
        global _busy
        while True:
            chunk=self.chunk_queue.get()
            if chunk is None and _busy==False:
                _busy=True
                break
            self.tts.append_text(chunk)
            self.tts.commit()

    def start(self, voice_name="shu"):
        with open(os.path.join(BASE_DIR, "config.json"), "r") as f:
            config = json.load(f)
        voice_token=config[voice_name]["voice"]["voice_id"]
        self.tts.connect()
        self.tts.update_session(
            voice=voice_token,
            response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            mode='commit',
            speech_rate=1
        )
        self.commit_thread.start()

    def feed(self,text_chunk):
        self.buffer+=text_chunk
        if self.buffer and self.buffer[-1] in self.ending:
            self.chunk_queue.put(self.buffer)
            self.buffer=""

    def feed_rest(self):
        if self.buffer.strip():
            self.chunk_queue.put(self.buffer)
            self.buffer=""

    def finish(self):
        if self.buffer.strip():
            self.chunk_queue.put(self.buffer)
            self.buffer=""
        self.tts.finish()
        self.callback.wait_for_response_done()   # 修正方法名
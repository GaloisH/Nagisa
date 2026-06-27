import base64
import os
import threading
import uuid
import dashscope
from dashscope.audio.qwen_tts_realtime import *
import json
import queue
import threading
import time
import base64
import pyaudio
from dashscope.audio.qwen_tts_realtime import *
import logging

# 简单配置日志（可根据需要调整级别、格式）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# =========================================
# 全局状态
# =========================================
sentence_queue = queue.Queue()
DEFAULT_TARGET_MODEL = "qwen3-tts-vc-realtime-2026-01-15" 
current_sentence = ""
tts_busy = False
BASE_DIR= os.path.dirname(os.path.abspath(__file__))
VOICE_NAME = "Arknights_shu"


# 工具函数
def is_sentence_end(text: str):
    if not text:
        return False
    return text[-1] in ['。', '！', '？', '.', '!', '?']


def init_dashscope_api_key():
    if 'DASHSCOPE_API_KEY' in os.environ:
        dashscope.api_key = os.environ[
            'DASHSCOPE_API_KEY']  # load API-key from environment variable DASHSCOPE_API_KEY
    else:
        dashscope.api_key = 'your-dashscope-api-key'  # set API-key manually


# 提交下一句（核心）
def try_commit_next(qwen_tts=None):
    global tts_busy
    # 当前TTS还在生成
    if tts_busy:
        return
    
    # 没有待播句子
    if sentence_queue.empty():
        return
    
    sentence = sentence_queue.get()
    # print(f'[TTS] commit sentence: {sentence}')
    tts_busy = True
    qwen_tts.append_text(sentence)
    
    event_id = "event_" + uuid.uuid4().hex
    logger.info(f'手动提交了commit，eventId: {event_id}')
    qwen_tts.send_raw(json.dumps({
      "event_id": event_id,
      "type": "input_text_buffer.commit",
    }))


# =========================================
# TTS 回调
# =========================================

class MyCallback(QwenTtsRealtimeCallback):
    def __init__(self):
        self._player = pyaudio.PyAudio()
        self._stream = self._player.open(
            format= pyaudio.paInt16, channels=1, rate=24000, output=True
        )
        self.tts = None
        self.ifCanWrite = True
        self.pcm_buffer = None

    def on_open(self):
        print('[TTS] websocket connected')

    def on_close(self, code, msg):
        print('[TTS] websocket closed')

    def on_event(self, response):
        global tts_busy
        event_type = response['type']
        # 音频chunk到达事件（一次commit的文本会触发多个delta事件）
        if event_type == 'response.audio.delta':
            audio_b64 = response['delta']
            pcm_bytes = base64.b64decode(audio_b64)
            self.pcm_buffer.put(pcm_bytes)

            
            # print(f'[Audio] recv {len(pcm_bytes)} bytes')if self.ifCanWrite:self._stream.write(pcm_bytes)
        
        # 某个commit的chunk流结束
        elif event_type == 'response.done':
            # print('[TTS] response done')
            # 当前response结束
            tts_busy = False
            logger.info('尝试提交下一句')
            # 自动触发下一句
            try_commit_next(self.tts)

    def print_itemId_eventId(self, response, event_type):
        
        if event_type == 'input_text_buffer.committed':
            logger.info('服务端 committed 事件触发')
            logger.info(f'item_id: {response["item_id"]}, event_id: {response["event_id"]}')
        
        elif event_type == 'response.audio.delta':
            logger.info('audio.delta 事件触发')
            logger.info(f"response Id {response['response_id']}, item_id: {response['item_id']}, event_id: {response['event_id']}")
        
        elif event_type == 'response.done':
            logger.info('response.done 事件触发')
            # output 是列表，取第一个元素的 id（若存在）
            output_list = response['response']['output']
            if output_list and isinstance(output_list, list):
                output_id = output_list[0].get('id', 'N/A')
            else:
                output_id = 'None'
            logger.info(f"response Id {response['response']['id']}, output item_id: {output_id}, event_id: {response['event_id']}")


class StreamingTTS():
    # 初始化环境
    def __init__(self,model=DEFAULT_TARGET_MODEL, url='wss://dashscope.aliyuncs.com/api-ws/v1/realtime'):
        init_dashscope_api_key()
        self.callback = MyCallback()
        self.tts = QwenTtsRealtime(
            model=model,
            callback=self.callback,
            url=url
        )
        self.callback.tts = self.tts
        self.pcm_buffer = queue.Queue()
        self.callback.pcm_buffer = self.pcm_buffer

    # 读取本地文件的voice_id，与云端建立websockt连接，并上传音色参数voice_id
    def start(self, voice_name=VOICE_NAME):
        with open(os.path.join(BASE_DIR, "config.json"), "r") as f:
            config = json.load(f)
        voice_id =config[voice_name]["voice"]["voice_id"]
        self.tts.connect()
        self.tts.update_session(
            voice=voice_id,
            response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            mode='commit',
            speech_rate=1
        )
        # 3. 启动发送线程
        self.writer = threading.Thread(target=self.write_loop, daemon=True)
        self.writer.start()


    def write_loop(self):
        while True:
            try:
                if self.callback.ifCanWrite:
                    pcm_bytes = self.pcm_buffer.get(timeout=0.5)
                    self.callback._stream.write(pcm_bytes)
                else:
                    time.sleep(0.2)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[WriteLoop error] {e}")
                break

    
        
    # tts 是否要加global
    def process_llm_chunk(self, chunk):
        global current_sentence
        current_sentence += chunk
        # 断句
        if is_sentence_end(current_sentence):
            sentence = current_sentence.strip()
            current_sentence = ""
            sentence_queue.put(sentence)
            # print(f'[Queue] add sentence: {sentence}')
            # 尝试提交
            try_commit_next(self.tts)

    def finish(self):
        self.tts.finish()
        self.callback.wait_for_finished()
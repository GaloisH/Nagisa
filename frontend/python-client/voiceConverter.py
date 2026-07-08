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
DEFAULT_TARGET_MODEL = "qwen3-tts-vc-realtime-2026-01-15" 
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
def try_commit_next(qwen_tts=None,sentence_queue=None,callbackObject=None):
    global tts_busy
    # 当前TTS还在生成
    if tts_busy:
        return
    with callbackObject.condition:
        # 没有待播句子
        if sentence_queue.empty():
            return
        
        sentence = sentence_queue.get()
        # print(f'[TTS] commit sentence: {sentence}')
        tts_busy = True
        qwen_tts.append_text(sentence)
        
        event_id = "event_" + uuid.uuid4().hex
        logger.info(f'手动提交了commit，eventId: {event_id}')
    
        callbackObject.isAck = False  # 重置标记，等待服务端的第一个delta事件
        qwen_tts.send_raw(json.dumps({
            "event_id": event_id,
            "type": "input_text_buffer.commit",
        }))


# =========================================
# TTS 回调
# =========================================

class MyCallback(QwenTtsRealtimeCallback):
    def __init__(self, sentence_queue=None):
        self._player = pyaudio.PyAudio()
        self._stream = self._player.open(
            format= pyaudio.paInt16, channels=1, rate=24000, output=True
        )
        self.tts = None
        self.ifCanWrite = True
        self.pcm_buffer = None
        self.sentence_queue = sentence_queue
        self.condition = threading.Condition()  # 保证串行
        self.isAck = False  # 用于标记是否收到服务端的第一个delta事件
        self.abandonedItemId = None  # 用于记录语音清空后，被放弃的itemId
        self.currentItemId = None  # 用于记录已提交commit 的 对应回复的 itemId
        

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
            with self.condition:
                # 1.如果当前是第一个 delta 事件，则设置 currentItemId
                if self.isAck == False:
                    self.isAck = True
                    self.currentItemId = response["item_id"]
                    logger.info(f'首个delta事件触发，itemId: {response["item_id"]}')
                    self.pcm_buffer.put(pcm_bytes)
                    self.condition.notify_all()  # 唤醒等待的线程
                else:
                    # 2.如果当前不是第一个delta事件，需判断 abandonedItemId 是否设置并匹配
                    # 如果匹配则不放入队列
                    if self.abandonedItemId and response["item_id"] == self.abandonedItemId:
                        logger.info(f'丢弃被放弃的itemId的delta事件，itemId: {response["item_id"]}')
                    else:
                        # 3.当前不是第一个delta事件，但itemId正常，则放入队列
                        self.pcm_buffer.put(pcm_bytes)

            
            # print(f'[Audio] recv {len(pcm_bytes)} bytes')if self.ifCanWrite:self._stream.write(pcm_bytes)
        
        # 某个commit的chunk流结束
        elif event_type == 'response.done':
            # print('[TTS] response done')
            # 当前response结束

            # 避免没有delta事件，做一个兜底
            with self.condition:
                if self.isAck == False:
                    self.isAck = True
                    logger.info(f'没有delta事件，直接触发done事件，response: {response}')
                    self.condition.notify_all()  # 唤醒等待的线程

            tts_busy = False
            logger.info('尝试提交下一句')
            # 自动触发下一句
            try_commit_next(self.tts, self.sentence_queue, self)

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
        self.sentence_queue = queue.Queue()
        self.callback = MyCallback(sentence_queue=self.sentence_queue)
        self.tts = QwenTtsRealtime(
            model=model,
            callback=self.callback,
            url=url
        )
        self.callback.tts = self.tts
        self.pcm_buffer = queue.Queue()
        self.callback.pcm_buffer = self.pcm_buffer
        self.currentSentence = ""  # 用于缓存当前正在生成的句子
        self.currentSentenceCondition = threading.Condition()  # 用于保护 currentSentence 的访问

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
        with self.currentSentenceCondition:
            self.currentSentence += chunk
        # 断句
        if is_sentence_end(self.currentSentence):
            with self.currentSentenceCondition:
                sentence = self.currentSentence.strip()
                self.currentSentence = ""
            self.sentence_queue.put(sentence)
            # print(f'[Queue] add sentence: {sentence}')
            # 尝试提交
            try_commit_next(self.tts, self.sentence_queue, self.callback)

    def finish(self):
        self.tts.finish()
        self.callback.wait_for_finished()
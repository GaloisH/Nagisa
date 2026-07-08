import sys
import threading
import time
import queue
import logging

# 简单配置日志（可根据需要调整级别、格式）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QTextEdit
)

from PyQt6.QtCore import (
    Qt,
    QObject,
    pyqtSignal
)

from PyQt6.QtGui import QPixmap

from pynput import keyboard

from new_web_client import WebSocketClient

from speechToText import RealtimeSTT

import os

BASE_DIR = os.path.dirname(__file__)

IMAGE_PATH = os.path.join(
    BASE_DIR,
    "characters",
    "shu",
    "Avg_avg_2025_shu_1-1$1.png"
)

stop_event  = threading.Event()


def clear_queue_safely(q):
        while not q.empty():
            try:
                # 使用非阻塞 get，避免在队列为空时永久阻塞
                q.get_nowait()
            except queue.Empty:
                break

# --------------------
# GUI线程安全信号
# --------------------

class GuiSignal(QObject):

    update_text_signal = pyqtSignal(str)



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
        elif key == keyboard.Key.delete:
            print("\n[键盘线程] 停止扬声器流写入")
            self._tts.callback.ifCanWrite = False
        elif key == keyboard.Key.alt_l:
            print("\n[键盘线程] 恢复扬声器流写入")
            self._tts.callback.ifCanWrite = True

    # 设置暂停标识后，调用stt.pause停止音频采集，之后等待语音队列中的数据被全部发送至云端，然后commit
    def _on_release(self, key):
        if key == keyboard.Key.space:
            self._recording = False
            print("\n[键盘线程] 暂停 STT 采集")
            # 1. stt 音频采集关闭
            self._stt.pause()
            # 2.等待语音队列发送完毕
            while not self._stt.audio_queue.empty():
                try:
                    time.sleep(0.1)
                except queue.Empty:
                    break
            # 3.手动 commit
            self._stt.completed_event.clear() # 复用event
            self._stt.conversation.commit()
            # 4.等待这次commit的complete事件，拿到最终转录结果
            completed = self._stt.completed_event.wait(timeout=10)  # 阻塞等待最多10秒
            if completed:
                print("keyboard listener detected commit completed event!")
                text = self._stt.transcript_queue.get_nowait()
                print(f"\n[键盘线程] 文本入队: {text}")
            else:
                print("keyboard listener wait for completed event but timed out!")



# --------------------
# 主窗口
# --------------------

class AssistantWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("桌面助手")

        self.setGeometry(
            200,
            200,
            400,
            650
        )

        # ---------- 信号 ----------

        self.signal = GuiSignal()

        self.signal.update_text_signal.connect(
            self.update_dynamic_text
        )

        # ---------- Layout ----------

        main_layout = QVBoxLayout()

        self.setLayout(main_layout)

        # ---------- 立绘 ----------

        self.avatar_label = QLabel()

        self.avatar_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.avatar_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        main_layout.addWidget(
            self.avatar_label,
            stretch=7
        )

        
        self.load_avatar(IMAGE_PATH)

        # ---------- AI字幕 ----------

        self.dynamic_text = QTextEdit()

        # 用户不能编辑
        self.dynamic_text.setReadOnly(True)

        # 固定字幕区域高度
        self.dynamic_text.setFixedHeight(180)

        main_layout.addWidget(
            self.dynamic_text,
            stretch=2
        )

        # ---------- 输入区域 ----------

        input_layout = QHBoxLayout()

        self.input_line = QLineEdit()

        self.input_line.setPlaceholderText(
            "输入文本..."
        )

        self.input_line.returnPressed.connect(
            self.send_text
        )

        input_layout.addWidget(
            self.input_line
        )

        self.send_btn = QPushButton(
            "➤"
        )

        self.send_btn.clicked.connect(
            self.send_text
        )

        input_layout.addWidget(
            self.send_btn
        )

        main_layout.addLayout(
            input_layout
        )

        # ---------- 新增：语音的暂停/恢复按钮和清空按钮 ----------
        control_layout = QHBoxLayout()

        # 暂停/播放按钮（初始为 "⏸️"，表示当前可播放）
        self.pause_btn = QPushButton("⏸️")
        self.pause_btn.clicked.connect(self.toggle_pause)
        control_layout.addWidget(self.pause_btn)

        # 语音清空按钮（仅样式，不绑定回调）
        self.clear_btn = QPushButton("🗑️ 清空语音")
        self.clear_btn.clicked.connect(self.toggle_clear)
        control_layout.addWidget(self.clear_btn)

        main_layout.addLayout(control_layout)



        # ---------- 初始化 WebSocket ----------

        self.client = WebSocketClient(
            "ws://localhost:8600/ws",
            text_callback=self.receive_ws_text
        )

        threading.Thread(
            target=self.client.connect,
            daemon=True
        ).start()


        # ---------- 初始化 STT ----------
        self.stt = RealtimeSTT(
            text_callback=self.receive_stt_text
        )
        self.stt.start()
        self.stt.pause()

        # ---------- 初始化键盘监听 ----------
        keyboard_ctrl = KeyboardController(self.stt, stop_event)
        keyboard_ctrl.start()


    # 清空缓冲区语音以及本轮对话还未播放的语音
    def toggle_clear(self):
        # 1. 首先禁止扬声器播放
        self.client.tts.callback.ifCanWrite = False

        # 2.本轮对话还未返回的文本取消语音转化，下次发消息时恢复
        self.client.should_tts = False  
        logger.info("self.client.should_tts set to False")

        # 2.5 currentSentence清空，为确保清空，下轮对话发送时再次清空
        with self.client.tts.currentSentenceCondition:
            self.client.tts.currentSentence = ""
            logger.info("currentSentence cleared")
 
        with self.client.tts.callback.condition:
            # 3. 清空语音缓冲区
            clear_queue_safely(self.client.tts.sentence_queue)

            # 4. 清空语音缓冲区后，有至多一条 commit 的消息尚未响应，等待其第一个delta事件响应
        
            # 4.1 首先判断第一个delta事件是否已经触发，如果触发了，说明当前commit的语音已经开始生成了，直接将其标记为abandonedItemId
            if self.client.tts.callback.isAck:
                self.client.tts.callback.abandonedItemId = self.client.tts.callback.currentItemId
                logger.info(f'清空语音后，标记abandonedItemId: {self.client.tts.callback.abandonedItemId}')
            else:
                # 4.2 如果第一个delta事件还未触发，说明当前commit的语音还未生成，等待其第一个delta事件触发后再标记abandonedItemId
                logger.info('清空语音后，等待首个delta事件触发以标记abandonedItemId')
                # 防止虚假唤醒
                while not self.client.tts.callback.isAck:
                    self.client.tts.callback.condition.wait()  # 阻塞等待首个delta事件触发(释放锁)
                logger.info(f'首个delta事件触发后，标记abandonedItemId: {self.client.tts.callback.currentItemId}')
                self.client.tts.callback.abandonedItemId = self.client.tts.callback.currentItemId

        # 5.清空云端返回语音缓冲区
        clear_queue_safely(self.client.tts.pcm_buffer)

        # 6. 清空语音后，恢复扬声器播放
        self.client.tts.callback.ifCanWrite = True
        logger.info("语音清空成功")
        return
    
    

    



    def toggle_pause(self):
        """切换 TTS 播放暂停/恢复，并更新按钮图标"""
        if self.client.tts.callback.ifCanWrite:
            # 当前允许写入 → 暂停播放
            self.client.tts.callback.ifCanWrite = False
            self.pause_btn.setText("▶️")   # 变为“播放”图标
        else:
            # 当前暂停 → 恢复播放
            self.client.tts.callback.ifCanWrite = True
            self.pause_btn.setText("⏸️")   # 变为“暂停”图标

    # --------------------
    # websocket回调
    # --------------------

    def receive_ws_text(self, text):

        self.signal.update_text_signal.emit(
            text
        )

    # --------------------
    # stt文本更新回调
    # --------------------
    def receive_stt_text(self, text):

        self.input_line.setText(
            text
        )
    

    # --------------------
    # UI更新
    # --------------------

    # def update_dynamic_text(self, text):

    #     cursor = self.dynamic_text.textCursor()

    #     cursor.movePosition(
    #         cursor.MoveOperation.End
    #     )

    #     cursor.insertText(text)

    #     self.dynamic_text.setTextCursor(
    #         cursor
    #     )

    #     # 自动滚到底部
    #     self.dynamic_text.ensureCursorVisible()

    #     # 限制最大字符数
    #     MAX_CHARS = 1200

    #     content = self.dynamic_text.toPlainText()

    #     if len(content) > MAX_CHARS:

    #         self.dynamic_text.setPlainText(
    #             content[-MAX_CHARS:]
    #         )

    #         cursor = self.dynamic_text.textCursor()

    #         cursor.movePosition(
    #             cursor.MoveOperation.End
    #         )

    #         self.dynamic_text.setTextCursor(
    #             cursor
    #         )

    def update_dynamic_text(self, text):

        cursor = self.dynamic_text.textCursor()

        cursor.movePosition(
            cursor.MoveOperation.End
        )

        cursor.insertText(text)

        self.dynamic_text.setTextCursor(
            cursor
        )

        # 自动滚动到底部
        self.dynamic_text.ensureCursorVisible()

    # --------------------
    # 发消息
    # --------------------

    def send_text(self):

        text = self.input_line.text().strip()

        if not text:
            return

        self.input_line.clear()

        self.client.should_tts = True  # 发送消息时恢复 TTS
        print("self.client.should_tts set to True")
        self.client.tts.currentSentence = ""

        self.client.send_message(
            text
        )

    # --------------------
    # 换立绘
    # --------------------

    def load_avatar(
            self,
            image_path
    ):

        pixmap = QPixmap(
            image_path
        )

        if pixmap.isNull():

            print(
                "图片加载失败:",
                image_path
            )

            return

        self.avatar_label.setPixmap(

            pixmap.scaled(

                300,
                450,

                Qt.AspectRatioMode.KeepAspectRatio,

                Qt.TransformationMode.SmoothTransformation
            )
        )


# --------------------
# main
# --------------------

if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    window = AssistantWindow()

    window.show()

    sys.exit(
        app.exec()
    )
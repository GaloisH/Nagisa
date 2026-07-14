from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QThread, QPoint

from .chat_display import ChatDisplay
from .input_bar import InputBar
from .worker import AgentWorker
from .live2d import Live2DWidget
from logger import get_logger


class VoiceAgentWindow(QMainWindow):
    def __init__(self, agent):
        super().__init__()
        self._logger = get_logger(__name__)
        self.agent = agent

        self._logger.debug("开始初始化 VoiceAgentWindow")

        self.setWindowTitle("Voice Agent - Nagisa")
        self.resize(500, 700)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._is_tracking = False
        self._start_pos = QPoint()

        self._logger.debug("窗口属性设置完成 (size=500x700, frameless, always-on-top, translucent)")

        self._init_ui()

        self.worker_thread = QThread()
        self.worker = AgentWorker(self.agent)
        self.worker.moveToThread(self.worker_thread)

        self.worker.state_changed.connect(self._on_state_changed)
        self.worker.transcript_ready.connect(self._on_transcript_ready)
        self.worker.response_chunk.connect(self._on_response_chunk)
        self.worker.response_done.connect(self._on_response_done)
        self.worker.error_occurred.connect(self._on_error)

        self.worker_thread.start()
        self._logger.debug("AgentWorker 已移入后台线程并启动")

        self._logger.info("VoiceAgentWindow 初始化完成")

    def _init_ui(self):
        self._logger.debug("开始构建 UI")

        central_widget = QWidget()
        central_widget.setStyleSheet("background:transparent;")

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(10)

        # ── 上半部分：人物立绘(左) + 字幕区(右) ──────────────────────────
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)

        # 左：Live2D 角色
        self.live2d_widget = Live2DWidget(url="http://localhost:5000/")
        self.live2d_widget.setMinimumWidth(400)

        # 右：状态栏 + 聊天字幕（全透明）
        right_panel = QWidget()
        right_panel.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # 聊天字幕区（全屏幕独立字幕层）
        self.chat_display = ChatDisplay()
        self.chat_display.show()
        self._logger.debug("ChatDisplay 独立悬浮窗已显示")

        top_layout.addWidget(self.live2d_widget)
        top_layout.addStretch(1)

        # ── 底部：输入框 ─────────────────────────────────────────────
        self.input_bar = InputBar()

        root_layout.addLayout(top_layout, stretch=1)
        root_layout.addWidget(self.input_bar)

        self.setCentralWidget(central_widget)

        self.input_bar.send_requested.connect(self._on_send_requested)
        self.input_bar.ptt_pressed.connect(self._on_ptt_pressed)
        self.input_bar.ptt_released.connect(self._on_ptt_released)
        self._logger.debug("InputBar 信号已连接 (send_requested, ptt_pressed, ptt_released)")

        self._logger.debug("UI 构建完成")

    # ── 业务逻辑 ──────────────────────────────────────────────────────

    def _on_send_requested(self, text):
        self._logger.info(f"收到发送请求，文本长度: {len(text)}")
        self._logger.debug(f"发送文本内容: {text}")

        if text.strip() == "/exit":
            self._logger.info("收到退出指令 /exit，关闭窗口")
            self.close()
            return

        self.chat_display.add_user_message(text)
        self.agent.submit_text(text)
        self._logger.debug("文本已提交给 Agent")

    def _on_ptt_pressed(self):
        self._logger.info("PTT 按下，开始聆听")
        self.chat_display.add_system_message("正在聆听...")
        self.agent.start_listening()
        self._logger.debug("已调用 agent.start_listening()")

    def _on_ptt_released(self):
        self._logger.info("PTT 松开，停止聆听")
        self.agent.stop_listening()
        self._logger.debug("已调用 agent.stop_listening()")

    def _on_state_changed(self, old_state, new_state):
        self._logger.debug(f"状态切换: {old_state} → {new_state}")

    def _on_transcript_ready(self, text):
        self._logger.info(f"STT 识别完成，文本长度: {len(text)}")
        self._logger.debug(f"STT 识别文本: {text}")
        self.chat_display.add_stt_transcript(text)
        self.chat_display.start_ai_message()

    def _on_response_chunk(self, chunk):
        if getattr(self.chat_display, 'is_speaking', False) is False:
            self.chat_display.start_ai_message()
            self._logger.debug("收到首个 response_chunk，启动 AI 消息显示")
        self.chat_display.append_ai_chunk(chunk)

    def _on_response_done(self, full_text):
        self._logger.info(f"AI 回复完成，总长度: {len(full_text)}")
        self._logger.debug(f"AI 完整回复: {full_text[:200]}{'...' if len(full_text) > 200 else ''}")
        self.chat_display.finish_ai_message(full_text)

    def _on_error(self, error_msg):
        self._logger.error(f"Agent 回调错误: {error_msg}")
        self.chat_display.add_system_message(f"错误: {error_msg}")

    # ── 拖拽支持 ─────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_tracking = True
            self._start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._is_tracking:
            new_pos = event.globalPosition().toPoint() - self._start_pos
            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_tracking = False

    def closeEvent(self, event):
        self._logger.info("窗口关闭事件触发")
        self._logger.debug("开始清理资源: ChatDisplay → Agent → WorkerThread")
        self.chat_display.close()
        self._logger.debug("ChatDisplay 已关闭")
        self.agent.stop()
        self._logger.debug("Agent 已停止")
        self.worker_thread.quit()
        self.worker_thread.wait(3000)
        self._logger.debug("WorkerThread 已退出")
        self._logger.info("VoiceAgentWindow 关闭完成")
        super().closeEvent(event)

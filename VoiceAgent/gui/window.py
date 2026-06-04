from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QThread, QPoint
from PyQt6.QtGui import QPixmap

from .chat_display import ChatDisplay
from .input_bar import InputBar
from .worker import AgentWorker

class VoiceAgentWindow(QMainWindow):
    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        
        self.setWindowTitle("Voice Agent - Nagisa")
        self.resize(800, 400)
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 移除全局窗口透明度限制，改为在各自组件内设置 rgba 透明度

        self._is_tracking = False
        self._start_pos = QPoint()

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

    def _init_ui(self):
        central_widget = QWidget()
        # 整个中央容器透明，无背景
        central_widget.setStyleSheet("background:transparent;")

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(10)

        # ── 上半部分：人物立绘(左) + 字幕区(右) ──────────────────────────
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)

        # 左：人物立绘（全透明，仅占位）
        # 左：角色立绘
        self.portrait_label = QLabel()

        self.portrait_label.setAlignment(
            Qt.AlignmentFlag.AlignBottom |
            Qt.AlignmentFlag.AlignHCenter
        )

        # ===== 用户只需要修改这里 =====
        portrait_path = r"D:\python_code\projects\Nagisa\VoiceAgent\gui\assets\image.png"
        # ===========================

        pixmap = QPixmap(portrait_path)

        if not pixmap.isNull():

            # 缩放立绘（保持比例）
            scaled_pixmap = pixmap.scaled(
                400,                     # 最大宽度
                700,                     # 最大高度
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            self.portrait_label.setPixmap(scaled_pixmap)

        else:
            self.portrait_label.setText(
                f"立绘加载失败:\n{portrait_path}"
            )

            self.portrait_label.setStyleSheet("""
                QLabel {
                    color: rgba(255,255,255,120);
                    font-size: 16px;
                    background: transparent;
                }
            """)

        self.portrait_label.setMinimumWidth(400)

        self.portrait_label.setStyleSheet("""
            QLabel {
                background: transparent;
            }
        """)

        # 右：状态栏 + 聊天字幕（全透明）
        right_panel = QWidget()
        right_panel.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # 聊天字幕区（全屏幕独立字幕层）
        self.chat_display = ChatDisplay()
        self.chat_display.show()

        top_layout.addWidget(self.portrait_label)
        top_layout.addStretch(1) # 占位

        # ── 底部：输入框（唯一有背景色的区域）─────────────────────────────
        self.input_bar = InputBar()
        # InputBar 自身的 #inputBarBox 样式已带背景，这里不需要额外设置

        root_layout.addLayout(top_layout, stretch=1)
        root_layout.addWidget(self.input_bar)

        self.setCentralWidget(central_widget)

        self.input_bar.send_requested.connect(self._on_send_requested)
        self.input_bar.ptt_pressed.connect(self._on_ptt_pressed)
        self.input_bar.ptt_released.connect(self._on_ptt_released)

    # ── 业务逻辑（不变）──────────────────────────────────────────────────

    def _on_send_requested(self, text):
        if text.strip() == "/exit":
            self.close()
            return
        self.chat_display.add_user_message(text)
        self.agent.submit_text(text)
        
    def _on_ptt_pressed(self):
        print("[UI] PTT 按下，开始聆听...")
        self.chat_display.add_system_message("正在聆听...")
        self.agent.start_listening()
        
    def _on_ptt_released(self):
        print("[UI] PTT 松开，停止聆听")
        self.agent.stop_listening()

    def _on_state_changed(self, old_state, new_state):
        pass

    def _on_transcript_ready(self, text):
        self.chat_display.add_stt_transcript(text)
        self.chat_display.start_ai_message()

    def _on_response_chunk(self, chunk):
        if getattr(self.chat_display, 'is_speaking', False) is False:
            self.chat_display.start_ai_message()
        self.chat_display.append_ai_chunk(chunk)

    def _on_response_done(self, full_text):
        self.chat_display.finish_ai_message(full_text)

    def _on_error(self, error_msg):
        self.chat_display.add_system_message(f"错误: {error_msg}")

    # ── 拖拽支持 ─────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_tracking = True
            self._start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._is_tracking:
            self.move(event.globalPosition().toPoint() - self._start_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_tracking = False

    def closeEvent(self, event):
        self.chat_display.close()
        self.agent.stop()
        self.worker_thread.quit()
        self.worker_thread.wait(3000)
        super().closeEvent(event)
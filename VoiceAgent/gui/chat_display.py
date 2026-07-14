from PyQt6.QtWidgets import QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QGuiApplication
from logger import get_logger


class ChatDisplay(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = get_logger(__name__)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self.setWordWrap(True)
        self.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 32px;
                font-weight: bold;
                font-family: "Microsoft YaHei", sans-serif;
                background: transparent;
                padding: 10px;
            }
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(2, 2)
        self.setGraphicsEffect(shadow)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        w = int(screen.width() * 0.8)
        h = 250
        x = screen.x() + (screen.width() - w) // 2
        y = screen.y() + screen.height() - h - 40
        self.setGeometry(x, y, w, h)

        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self._toggle_cursor)
        self.cursor_visible = False
        self.current_ai_text = ""
        self.is_speaking = False

        self._logger.info("ChatDisplay 初始化完成")

    def clear_messages(self):
        self._logger.debug("清除屏幕字幕")
        self.setText("")

    def add_user_message(self, text):
        self._logger.info(f"显示用户消息，长度: {len(text)}")
        self._logger.debug(f"用户消息内容: {text}")
        self.setText(f"你: {text}")

    def add_stt_transcript(self, text):
        self._logger.info(f"显示 STT 转录文本，长度: {len(text)}")
        self._logger.debug(f"STT 转录内容: {text}")
        self.setText(f"🎤 {text}")

    def add_system_message(self, text):
        self._logger.debug(f"系统消息: {text}")

    def start_ai_message(self, avatar_name=None):
        self._logger.info("模型开始回复")
        self._logger.debug(f"start_ai_message: avatar_name={avatar_name}, 当前文本长度={len(self.current_ai_text)}")
        self.current_ai_text = ""
        self.is_speaking = True
        self.cursor_timer.start(500)
        self._update_ai_label()

    def append_ai_chunk(self, chunk):
        self._logger.debug(f"追加模型回复chunk: '{chunk}'")
        self.current_ai_text += chunk
        self._update_ai_label()

    def finish_ai_message(self, full_text=None):
        self._logger.info(f"AI 结束说话，文本长度: {len(full_text) if full_text else len(self.current_ai_text)}")
        self._logger.debug(f"finish_ai_message: full_text={'已提供' if full_text is not None else '未提供'}")
        if full_text is not None:
            self.current_ai_text = full_text
        self.cursor_timer.stop()
        self.cursor_visible = False
        self.is_speaking = False
        self.setText(self.current_ai_text)

        self._logger.debug("自动清除屏幕字幕")
        QTimer.singleShot(8000, self.clear_messages)

    def _toggle_cursor(self):
        self.cursor_visible = not self.cursor_visible
        self._update_ai_label()

    def _update_ai_label(self):
        display_text = self.current_ai_text + ("▌" if self.cursor_visible else "")
        self.setText(display_text)

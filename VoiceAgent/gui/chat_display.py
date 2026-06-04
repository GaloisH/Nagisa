from PyQt6.QtWidgets import QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QGuiApplication

class ChatDisplay(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设为无边框、置顶、鼠标穿透的独立悬浮窗
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool | 
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self.setWordWrap(True)
        # 屏幕下方居中大字号字幕样式
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
        
        # 使用 availableGeometry 避免边界越界，宽度限制为屏幕的80%并居中
        screen = QGuiApplication.primaryScreen().availableGeometry()
        w = int(screen.width() * 0.8)
        h = 250
        x = screen.x() + (screen.width() - w) // 2
        # 底部留一点边距（避免和任务栏冲突）
        y = screen.y() + screen.height() - h - 40
        self.setGeometry(x, y, w, h)

        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self._toggle_cursor)
        self.cursor_visible = False
        self.current_ai_text = ""
        self.is_speaking = False

    def clear_messages(self):
        self.setText("")

    def add_user_message(self, text):
        self.setText(f"你: {text}")

    def add_stt_transcript(self, text):
        self.setText(f"🎤 {text}")

    def add_system_message(self, text):
        pass 

    def start_ai_message(self, avatar_name=None):
        self.current_ai_text = ""
        self.is_speaking = True
        self.cursor_timer.start(500)
        self._update_ai_label()

    def append_ai_chunk(self, chunk):
        self.current_ai_text += chunk
        self._update_ai_label()

    def finish_ai_message(self, full_text=None):
        if full_text is not None:
            self.current_ai_text = full_text
        self.cursor_timer.stop()
        self.cursor_visible = False
        self.is_speaking = False
        self.setText(self.current_ai_text)
        
        # AI说完后8秒自动清空屏幕字幕
        QTimer.singleShot(8000, self.clear_messages)

    def _toggle_cursor(self):
        self.cursor_visible = not self.cursor_visible
        self._update_ai_label()

    def _update_ai_label(self):
        display_text = self.current_ai_text + ("▌" if self.cursor_visible else "")
        self.setText(display_text)

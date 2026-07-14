from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from logger import get_logger


class InputBar(QWidget):
    send_requested = pyqtSignal(str)
    ptt_pressed = pyqtSignal()
    ptt_released = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = get_logger(__name__)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(10)

        self.setCursor(Qt.CursorShape.SizeAllCursor)

        self.setObjectName("inputBarBox")
        self.setStyleSheet("""
            QWidget#inputBarBox {
                background-color: rgba(30, 30, 35, 180);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 20px;
            }
        """)

        self._is_tracking = False
        self._start_pos = QPoint()

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("与 Nagisa 对话...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 15px;
                padding: 8px 15px;
                color: rgba(255, 255, 255, 230);
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(135, 206, 235, 150);
                background-color: rgba(255, 255, 255, 25);
            }
        """)
        self.input_field.returnPressed.connect(self._on_send)

        self.send_btn = QPushButton("发送")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(57, 180, 229, 180);
                color: white;
                border: none;
                border-radius: 15px;
                padding: 8px 18px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(57, 180, 229, 220); }
            QPushButton:pressed { background-color: rgba(57, 180, 229, 255); }
        """)
        self.send_btn.clicked.connect(self._on_send)

        self.ptt_btn = QPushButton("🎤")
        self.ptt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ptt_btn.setToolTip("按住说话")
        self.ptt_btn.setAutoRepeat(False)
        self.ptt_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 53, 69, 180);
                color: white;
                border: none;
                border-radius: 15px;
                padding: 8px 18px;
                font-size: 15px;
            }
            QPushButton:hover { background-color: rgba(220, 53, 69, 220); }
            QPushButton:pressed { background-color: rgba(220, 53, 69, 255); }
        """)
        self.ptt_btn.pressed.connect(self._on_ptt_pressed)
        self.ptt_btn.released.connect(self._on_ptt_released)

        self.layout.addWidget(self.input_field, stretch=1)
        self.layout.addWidget(self.send_btn)
        self.layout.addWidget(self.ptt_btn)

        self.input_field.setCursor(Qt.CursorShape.IBeamCursor)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ptt_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self._logger.info("InputBar 初始化完成")

    def _on_send(self):
        text = self.input_field.text().strip()
        if text:
            self._logger.info(f"发送消息，长度: {len(text)}")
            self._logger.debug(f"发送消息内容: {text}")
            self.send_requested.emit(text)
            self.input_field.clear()
            self._logger.debug("输入框已清空")
        else:
            self._logger.debug("发送按钮点击但输入框为空，忽略")

    def _on_ptt_pressed(self):
        self._logger.info("按钮按下")
        self.ptt_pressed.emit()
        self._logger.debug("ptt_pressed 信号发射")

    def _on_ptt_released(self):
        self._logger.info("按钮释放")
        self.ptt_released.emit()
        self._logger.debug("ptt_released 信号发射")

    def set_enabled(self, enabled: bool):
        self._logger.info(f"InputBar 状态切换: {'启用' if enabled else '禁用'}")
        self.input_field.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        self.ptt_btn.setEnabled(enabled)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_tracking = True
            window = self.window()
            if window:
                self._start_pos = event.globalPosition().toPoint() - window.frameGeometry().topLeft()
                self._logger.debug(f"InputBar 拖拽开始: start_pos=({self._start_pos.x()},{self._start_pos.y()})")

    def mouseMoveEvent(self, event):
        if self._is_tracking:
            window = self.window()
            if window:
                new_pos = event.globalPosition().toPoint() - self._start_pos
                window.move(new_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_tracking = False

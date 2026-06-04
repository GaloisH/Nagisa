from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt, QPoint

class InputBar(QWidget):
    send_requested = pyqtSignal(str)
    ptt_pressed = pyqtSignal()
    ptt_released = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground,
            True
        )
        self.layout = QHBoxLayout(self)
        # 为四周留出边缘作为可拖动的把手部分
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(10)
        
        # 将整个 InputBar 背景设置为可拖拽光标
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        
        self.setObjectName("inputBarBox")
        # 采用半透明暗色玻璃风格背景
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
        self.ptt_btn.pressed.connect(self.ptt_pressed)
        self.ptt_btn.released.connect(self.ptt_released)
        
        self.layout.addWidget(self.input_field, stretch=1)
        self.layout.addWidget(self.send_btn)
        self.layout.addWidget(self.ptt_btn)
        
        # 恢复子组件自身的鼠标指针样式，避免继承背景的 SizeAllCursor 
        self.input_field.setCursor(Qt.CursorShape.IBeamCursor)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ptt_btn.setCursor(Qt.CursorShape.PointingHandCursor)

    def _on_send(self):
        text = self.input_field.text().strip()
        if text:
            self.send_requested.emit(text)
            self.input_field.clear()
            
    def set_enabled(self, enabled: bool):
        self.input_field.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        self.ptt_btn.setEnabled(enabled)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_tracking = True
            # 获取相对于整个顶级窗口的偏移量
            window = self.window()
            if window:
                self._start_pos = event.globalPosition().toPoint() - window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._is_tracking:
            window = self.window()
            if window:
                window.move(event.globalPosition().toPoint() - self._start_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_tracking = False


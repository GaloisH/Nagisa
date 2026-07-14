from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView
from logger import get_logger


class Live2DWidget(QWidget):
    """Qt widget that embeds a Live2D Cubism 5 web page via QWebEngineView."""

    page_ready = pyqtSignal()
    model_error = pyqtSignal(str)

    def __init__(self, url: str = "http://localhost:5000/", parent=None):
        super().__init__(parent)
        self._logger = get_logger(__name__)
        self._url = url

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setMinimumSize(400, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._webview = QWebEngineView()
        self._webview.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._webview.setStyleSheet("background: transparent;")
        self._webview.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self._webview.load(QUrl(self._url))
        self._webview.loadFinished.connect(self._on_load_finished)

        layout.addWidget(self._webview)

        self._logger.info(f"Live2DWidget 初始化, URL={url}")

    def _on_load_finished(self, ok: bool):
        if ok:
            self._logger.info("Live2D 页面加载成功")
            self.page_ready.emit()
        else:
            self._logger.error(f"Live2D 页面加载失败: {self._url}")
            self.model_error.emit(f"页面加载失败: {self._url}")

    def run_js(self, code: str, callback=None):
        """Execute arbitrary JavaScript in the Live2D page."""
        if callback:
            self._webview.page().runJavaScript(code, callback)
        else:
            self._webview.page().runJavaScript(code)

    def set_expression(self, expression_id: str):
        """Switch facial expression."""
        js = f"if(typeof setExpression==='function') setExpression('{expression_id}');"
        self._logger.debug(f"设置表情: {expression_id}")
        self.run_js(js)

    def start_motion(self, group: str, index: int):
        """Play a motion from the given group."""
        js = f"if(typeof startMotion==='function') startMotion('{group}', {index});"
        self._logger.debug(f"播放动作: group='{group}', index={index}")
        self.run_js(js)

    def set_lip_sync(self, value: float):
        """Set lip-sync openness (0.0 ~ 1.0)."""
        js = f"if(typeof setLipSync==='function') setLipSync({value});"
        self.run_js(js)

    def set_param(self, param_id: str, value: float):
        """Set a raw Live2D parameter."""
        js = f"if(typeof setParam==='function') setParam('{param_id}', {value});"
        self.run_js(js)

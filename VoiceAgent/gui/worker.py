from PyQt6.QtCore import QObject, pyqtSignal
from logger import get_logger


class AgentWorker(QObject):
    state_changed = pyqtSignal(str, str)     # (old_state, new_state)
    transcript_ready = pyqtSignal(str)       # STT 识别文本
    response_chunk = pyqtSignal(str)         # LLM 流式 token
    response_done = pyqtSignal(str)          # LLM 完整回复
    error_occurred = pyqtSignal(str)         # 错误消息

    def __init__(self, agent=None, parent=None):
        super().__init__(parent)
        self._logger = get_logger(__name__)
        self._logger.debug(f"AgentWorker.__init__: agent={'已提供' if agent else '未提供'}, parent={parent}")

        self.agent = agent
        if self.agent:
            self.wire(self.agent)

        self._logger.info("AgentWorker 初始化完成")

    def wire(self, agent):
        self._logger.debug("开始绑定 Agent 回调到 Qt 信号")
        try:
            agent.on_state_change(self._emit_state_change)
            agent.on_transcript(self.transcript_ready.emit)
            agent.on_response_chunk(self.response_chunk.emit)
            agent.on_response_done(self.response_done.emit)
            agent.on_error(lambda e: self.error_occurred.emit(str(e)))
            self._logger.info("Agent 回调已绑定到 Qt 信号 (state_change, transcript, response_chunk, response_done, error)")
        except Exception:
            self._logger.exception("绑定 Agent 回调失败")

    def _emit_state_change(self, old_state, new_state):
        old_val = old_state.value if hasattr(old_state, 'value') else str(old_state)
        new_val = new_state.value if hasattr(new_state, 'value') else str(new_state)
        self._logger.debug(f"发射 state_changed 信号: {old_val} → {new_val}")
        self.state_changed.emit(old_val, new_val)

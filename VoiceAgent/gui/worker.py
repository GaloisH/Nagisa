from PyQt6.QtCore import QObject, pyqtSignal

class AgentWorker(QObject):
    state_changed = pyqtSignal(str, str)     # (old_state, new_state)
    transcript_ready = pyqtSignal(str)       # STT 识别文本
    response_chunk = pyqtSignal(str)         # LLM 流式 token
    response_done = pyqtSignal(str)          # LLM 完整回复
    error_occurred = pyqtSignal(str)         # 错误消息

    def __init__(self, agent=None, parent=None):
        super().__init__(parent)
        self.agent = agent
        if self.agent:
            self.wire(self.agent)

    def wire(self, agent):
        # 将 Agent 的回调连接到 Qt signals
        agent.on_state_change(self._emit_state_change)
        agent.on_transcript(self.transcript_ready.emit)
        agent.on_response_chunk(self.response_chunk.emit)
        agent.on_response_done(self.response_done.emit)
        agent.on_error(lambda e: self.error_occurred.emit(str(e)))
        
    def _emit_state_change(self, old_state, new_state):
        # 将枚举值转换为字符串
        old_val = old_state.value if hasattr(old_state, 'value') else str(old_state)
        new_val = new_state.value if hasattr(new_state, 'value') else str(new_state)
        self.state_changed.emit(old_val, new_val)

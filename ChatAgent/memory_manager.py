from mem0 import Memory
from config import Config
import logging

class MemoryManager:
    """
    负责与 mem0 交互，存储和检索长期记忆
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        # 初始化基于本地存储的记忆模块
        self.memory = Memory.from_config(Config.MEM0_CONFIG)
        logging.info(f"💾 Memory initialized for user: {self.user_id}")

    def add_interaction(self, user_message: str, agent_response: str):
        """保存对话交互作为记忆"""
        # mem0 会通过内置的大模型/Embedding机制自动分析、归纳并持久化
        # 我们可以传入一条完整的对话文本
        try:
            interaction = f"用户说: {user_message}\n你的回答: {agent_response}"
            self.memory.add(interaction, user_id=self.user_id)
        except Exception as e:
            logging.error(f"Add memory error: {e}")

    def get_relevant_memories(self, query: str, limit: int = 3) -> str:
        """从本地 mem0 存储中检索相关记忆"""
        try:
            results = self.memory.search(query, user_id=self.user_id, limit=limit)
        except Exception as e:
            # 防止首次初始化无集合时的报错
            logging.error(f"Search memory error: {e}")
            return ""

        if not results:
            return ""
            
        memories = []
        for item in results:
            if isinstance(item, dict):
                content = item.get("memory", item.get("text", str(item)))
            else:
                content = str(item)
            memories.append(f"  - {content}")
            
        return "\n".join(memories)

    def get_all_memories(self) -> str:
        """获取当前用户的所有记忆"""
        try:
            results = self.memory.get_all(user_id=self.user_id)
        except Exception as e:
            logging.error(f"Get all memories error: {e}")
            return ""

        if not results:
            return ""
            
        memories = []
        for item in results:
            if isinstance(item, dict):
                content = item.get("memory", item.get("text", str(item)))
            else:
                content = str(item)
            memories.append(f"  - {content}")
            
        return "\n".join(memories)

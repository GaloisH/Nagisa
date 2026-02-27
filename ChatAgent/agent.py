from memory_manager import MemoryManager
from llm_client import LLMClient
import logging

class RolePlayingAgent:
    """
    角色扮演核心逻辑
    将 记忆模块（MemoryManager）、模型模块（LLMClient） 组装，并管理对话上下文。
    """
    def __init__(self, name: str, role_description: str, user_id: str = "default_user"):
        self.name = name
        self.role_description = role_description
        
        # 实例化子模块
        self.memory_manager = MemoryManager(user_id=user_id)
        self.llm_client = LLMClient()
        
        # 维护一个滑动窗口的短期历史列表
        self.chat_history = []
        # 短期记忆保留对数 (一对为 User + Assistant)
        self.history_limit = 5

    def _build_system_prompt(self, relevant_memories: str) -> str:
        """构建系统提示词，其中注入角色设定的和刚刚提取出的长效记忆"""
        prompt = (
            f"你现在的身份是：{self.name}。\n"
            f"你的核心人设：{self.role_description}\n\n"
            "【行为准则】：\n"
            "1. 严格保持角色扮演，绝不能说自己是AI或语言模型。\n"
            "2. 你的语气要完全符合设定的人物特点。\n"
            "3. 你的回答不应过长，尽量贴近真人的对话习惯。\n"
        )
        
        if relevant_memories:
            prompt += (
                "\n【系统从过去提取的关于该用户的关键记忆】：\n"
                f"{relevant_memories}\n"
                "（请自然地在对话中表现出你对这些事情有印象，不要生硬地背诵记忆。）\n"
            )
            
        return prompt

    def process_message(self, user_message: str) -> str:
        """
        处理用户的输入并返回角色回复
        """
        # ================================
        # 1. 检索长效记忆
        # ================================
        logging.info(f"正在为输入检索记忆: '{user_message}'")
        print(self.memory_manager.get_all_memories())  # 调试：打印所有记忆内容
        memories = self.memory_manager.get_relevant_memories(user_message)
        if memories:
            logging.info(f"找到记忆:\n{memories}")
        else:
            logging.info("未找到相关记忆。")

        # ================================
        # 2. 构建给 LLM 的消息流
        # ================================
        system_prompt = self._build_system_prompt(memories)
        messages = [{"role": "system", "content": system_prompt}]
        
        # 填充短期历史上下文
        messages.extend(self.chat_history)
        
        # 加入当前用户消息
        messages.append({"role": "user", "content": user_message})

        # ================================
        # 3. 调用 LLM 大模型
        # ================================
        response = self.llm_client.chat(messages)

        # ================================
        # 4. 更新短期与长期记忆
        # ================================
        if not response.startswith("❌"):
            # 存入短期聊天记录
            self.chat_history.append({"role": "user", "content": user_message})
            self.chat_history.append({"role": "assistant", "content": response})
            
            # 短期上下文截断
            if len(self.chat_history) > self.history_limit * 2:
                self.chat_history = self.chat_history[-self.history_limit * 2:]

            # 存入 mem0 作为长效记忆 (后台会自动做 Embedding / 总结)
            # 因为 mem0 内部也会调用大模型进行归纳提取
            self.memory_manager.add_interaction(user_message, response)

        return response

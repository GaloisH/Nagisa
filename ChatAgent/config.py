import os
from dotenv import load_dotenv

# 加载当前目录下的 .env 环境变量
load_dotenv()

class Config:
    # ------------------
    # LLM API Config
    # ------------------
    LLM_API_KEY = os.getenv("API_KEY", os.getenv("OPENAI_API_KEY", ""))
    LLM_API_BASE = os.getenv("API_BASE", os.getenv("OPENAI_API_BASE", ""))
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    # 将读取到的配置同步到系统的环境变量中，防止 mem0 或内部 OpenAI 客户端找不到 key
    if LLM_API_KEY:
        os.environ["OPENAI_API_KEY"] = LLM_API_KEY
    if LLM_API_BASE:
        os.environ["OPENAI_API_BASE"] = LLM_API_BASE
        os.environ["OPENAI_BASE_URL"] = LLM_API_BASE

    # ------------------
    # mem0 Config
    # ------------------
    # 本地记忆库的相对路径
    MEMORY_DB_PATH = os.path.join(os.path.dirname(__file__), "mem0_db")

    # mem0 本地存储配置 (使用本地 chroma 或 qdrant)
    # 此处使用 chroma 作为免安装的本地向量存储方式
    MEM0_CONFIG = {
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "nagisa_roleplay_memories",
                "path": MEMORY_DB_PATH,
            }
        },
        # 如果你不想使用默认的 OpenAI Embeddings，也可以在这里配置 embedder
        # "embedder": {
        #     "provider": "openai",
        #     "config": {
        #         "model": "text-embedding-3-small"
        #     }
        # }
    }

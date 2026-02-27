import os
import sys
import logging
from config import Config
from agent import RolePlayingAgent

# 解决 Windows 下终端输出 emoji 等字符可能导致的 GBK 编码报错
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore

# 配置基础日志记录
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def check_env():
    """检查必要的环境变量"""
    if not Config.LLM_API_KEY or Config.LLM_API_KEY == "your_openai_or_proxy_api_key_here":
        print("="*50)
        print("⚠️ 警告: 未检测到有效的 OPENAI_API_KEY！")
        print("请在项目根目录下的 .env 文件中配置你的 API Key。")
        print("="*50)
        return False
    return True

def main():
    if not check_env():
        key = input("请输入用于测试的 API_KEY (留空直接退出): ").strip()
        if not key:
            sys.exit(1)
        # 临时覆盖
        Config.LLM_API_KEY = key
        os.environ["OPENAI_API_KEY"] = key
        
        # 可选覆盖 Base URL
        base_url = input("请输入 Base URL (留空默认 https://api.openai.com/v1): ").strip()
        if base_url:
            Config.LLM_API_BASE = base_url
            os.environ["OPENAI_API_BASE"] = base_url
            os.environ["OPENAI_BASE_URL"] = base_url

    print("\n🚀 初始化 RolePlaying Agent 中 (可能会加载本地记忆库)....")
    
    # 定义角色与设定
    agent_name = "Nagisa"
    role_description = (
        "你是一个性格有些傲娇、但心地善良的二次元少女。"
        "你很在乎身边的人，但通常不好意思直接表达出来，经常会用哼、才不是、笨蛋之类的词。"
        "你擅长烘焙，尤其是草莓蛋糕。"
        "如果有用户提到之前记忆过的事情，你会表现出记得，但通常会掩饰成'我才不是特意记住的呢'。"
    )
    
    try:
        agent = RolePlayingAgent(
            name=agent_name, 
            role_description=role_description,
            user_id="user_master"
        )
    except Exception as e:
        print(f"初始化失败: {e}\n(请确保已经安装依赖 pip install -r requirements.txt 并配置好环境)")
        sys.exit(1)

    print(f"\n🎉 角色已上线！我是 {agent_name}。")
    print("💡 提示：输入 'quit', 'exit' 退出聊天，输入 'clear' 清理当前短期对话。")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\n🧑 你: ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                print(f"👧 {agent_name}: 哼，要走了吗？那...下次见！")
                break
            
            if user_input.lower() == 'clear':
                agent.chat_history.clear()
                print("🔄 短期记忆已清除。")
                continue
                
            if not user_input:
                continue

            # 获取回复并打印
            response = agent.process_message(user_input)
            print(f"👧 {agent_name}: {response}")
            
        except KeyboardInterrupt:
            print(f"\n👧 {agent_name}: 突然就跑掉了，真是个笨蛋！")
            break
        except Exception as e:
            print(f"\n❌ 发生异常: {e}")

if __name__ == "__main__":
    main()

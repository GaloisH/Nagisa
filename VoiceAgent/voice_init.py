import dashscope
import os
from dotenv import load_dotenv
import pathlib
import base64
import requests
import json

load_dotenv()

DEFAULT_TARGET_MODEL = (
    "qwen3-tts-vc-realtime-2026-01-15"  # 声音复刻、语音合成要使用相同的模型
)
DEFAULT_PREFERRED_NAME = "xuanshen1"
DEFAULT_AUDIO_MIME_TYPE = "audio/mpeg"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_FILE_PATH = os.path.join(BASE_DIR, "tianhuangVoice.m4a")


def create_voice(
    file_path: str,
    target_model: str = DEFAULT_TARGET_MODEL,
    preferred_name: str = DEFAULT_PREFERRED_NAME,
    audio_mime_type: str = DEFAULT_AUDIO_MIME_TYPE,
) -> str:
    """
    创建音色，并返回 voice 参数
    """
    # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx"
    api_key = os.getenv("DASHSCOPE_API_KEY")

    file_path_obj = pathlib.Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"音频文件不存在: {file_path}")

    base64_str = base64.b64encode(file_path_obj.read_bytes()).decode()
    data_uri = f"data:{audio_mime_type};base64,{base64_str}"

    url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
    payload = {
        "model": "qwen-voice-enrollment",  # 不要修改该值
        "input": {
            "action": "create",
            "target_model": target_model,
            "preferred_name": preferred_name,
            "audio": {"data": data_uri},
        },
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"创建 voice 失败: {resp.status_code}, {resp.text}")

    try:
        voice = resp.json()["output"]["voice"]
        write_config(voice, preferred_name)
    except (KeyError, ValueError) as e:
        raise RuntimeError(f"解析 voice 响应失败: {e}")


def init_dashscope_api_key():
    """
    初始化 dashscope SDK 的 API key
    """
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")


def write_config(voice: str, preferred_name: str = DEFAULT_PREFERRED_NAME):
    config_path = os.path.join(BASE_DIR, "config.json")
    with open(config_path, "r") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError:
            print(
                "[WARN] config.json is not a valid JSON. Overwriting with new config."
            )
            config = {}
    voice_config = {"voice": {"voice_id": voice}}
    config[preferred_name] = voice_config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


if __name__ == "__main__":
    voice = create_voice(VOICE_FILE_PATH)

import json
import time
import base64
import sys
import threading
import select
import websocket
import cv2
import numpy as np
import pyautogui
import pyperclip
from mss import mss
from voiceConverter import StreamingTTS


class WebSocketClient:
    def __init__(self, url, text_callback=None):
        self.url = url
        self.text_callback = text_callback
        self.ws = None
        self.is_connected = False
        self.running = True
        self.should_tts = True  # 是否允许 TTS
        
        # 屏幕捕获初始化
        tmp_sct = mss()
        monitor = tmp_sct.monitors[1]
        self.screen_width = monitor["width"]
        self.screen_height = monitor["height"]
        tmp_sct.close()
        print(f"[INFO] 屏幕分辨率: {self.screen_width}x{self.screen_height}")

        # PyAutoGUI 配置
        pyautogui.PAUSE = 0.5
        pyautogui.FAILSAFE = True
        self.scale = 1 # 普通屏幕为1，高分屏按需调整
        self.tts = StreamingTTS()
        self.tts.start()

    # ---------------- 核心逻辑：消息处理 ----------------

    def on_message(self, ws, message):
        """收到服务端 BaseResponse 的处理逻辑"""
        try:
            response = json.loads(message)
            type = response.get("type")
            code = response.get("code")
            content = response.get("content")
            call_id = response.get("callId")
            actions = response.get("actions", [])
            end = response.get("end", False)

            # 1. 检查状态码
            if code != 200:
                print(f"\033[91m[ERROR] 服务端错误 ({code}): {response.get('message')}\033[0m")
                return
            
            # 2. 打印 AI 回应内容，调用 qwen_tts 处理语音合成
            if type and type == 'stream':

                if content:
                    print(content, end="", flush=True)

                    if self.text_callback:
                        self.text_callback(content)

                    if self.should_tts:
                        self.tts.process_llm_chunk(content)

                if end:
                    print("\n")

            else:
                if content and str(content).strip():

                    print(f"\n🤖 AI: {content}")

                    if self.text_callback:
                        self.text_callback(content)

                    self.tts.process_llm_chunk(content)


            # 3. 执行 Actions
            if call_id and actions:
                for action in actions:
                    self.execute_action(action, call_id)

        except Exception as e:
            print(f"\033[91m解析消息失败: {e}\033[0m")

    def execute_action(self, action, call_id):
        """执行单个指令并回传结果"""
        command = action.get("command")
        params = action.get("params", {})
        
        print(f"\033[94m[ACTION] 正在执行: {command} params: {params}\033[0m")
        
        try:
            # 特殊处理：截图
            if command.upper() == "SCREENSHOT":
                self.handle_screenshot(call_id)
                return

            # 通用处理：GUI 操作
            # 1. 坐标反归一化
            real_params = self.denormalize_coordinates(params)
            
            # 2. 动态调用匹配的方法
            if hasattr(self, command):
                func = getattr(self, command)
                result_msg = func(**real_params)
                self.send_base_request("action result", result_msg, 200, call_id)
            else:
                raise Exception(f"未定义的指令: {command}")

        except Exception as e:
            print(f"\033[91m执行动作失败: {e}\033[0m")
            self.send_base_request("action result", str(e), 504, call_id)

    def send_base_request(self, req_type, data, code, call_id):
        """发送 BaseRequest 到服务端"""
        payload = {
            "type": req_type,
            "data": data,
            "code": code,
            "callId": call_id
        }
        self.ws.send(json.dumps(payload))

    # ---------------- 工具函数：截图与坐标 ----------------

    def handle_screenshot(self, call_id):
        """处理截图指令：截图 -> 缩放 -> 编码 -> 发送"""
        try:
            # 1. 截屏
            with mss() as sct:
                screenshot = sct.grab(
                    sct.monitors[1]
                )
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # 2. 🚀 新增：图片缩放逻辑 (参照参考代码)
            max_size = 1024
            h, w = img.shape[:2]
            if max(h, w) > max_size:
                scale = max_size / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                # 使用 INTER_AREA 插值法，这是缩小图片时的最佳实践
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                print(f"[DEBUG] 缩放图片从 {w}x{h} 到 {new_w}x{new_h}")

            # 3. 编码为 JPEG (质量设为 85)
            success, buffer = cv2.imencode('.jpeg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            
            if not success:
                raise Exception("JPEG 编码失败")

            # 4. 转换为 Base64 字符串
            b64_str = base64.b64encode(buffer).decode('utf-8')
            
            # 5. 发送给后端
            self.send_base_request("screen shot", b64_str, 200, call_id)
            print("\033[94m[SUCCESS] 缩放后的 JPEG 截图已发送\033[0m")
            
        except Exception as e:
            print(f"\033[91m[ERROR] 截图失败: {e}\033[0m")
            self.send_base_request("screen shot", str(e), 504, call_id)

    def denormalize_coordinates(self, args):
        """将 0-1000 归一化坐标转换为像素坐标"""
        new_args = args.copy()
        # 处理常见坐标字段
        for key in ["x", "start_x", "end_x"]:
            if key in new_args:
                new_args[key] = int(new_args[key] * self.screen_width / 1000)
        for key in ["y", "start_y", "end_y"]:
            if key in new_args:
                new_args[key] = int(new_args[key] * self.screen_height / 1000)
        return new_args

    # ---------------- GUI 执行函数 ----------------

    def click_position(self, x, y, wait=1.5):
        pyautogui.moveTo(x, y, duration=0.3)
        pyautogui.click()
        time.sleep(wait)
        return f"Clicked at ({x}, {y})"

    def double_click_position(self, x, y, wait=1.5):
        pyautogui.moveTo(x, y, duration=0.3)
        pyautogui.doubleClick()
        time.sleep(wait)
        return f"Double clicked at ({x}, {y})"

    def right_click_position(self, x, y, wait=1.5):
        pyautogui.moveTo(x, y, duration=0.3)
        pyautogui.rightClick()
        time.sleep(wait)
        return f"Right clicked at ({x}, {y})"

    def type_text(self, text, press_enter=False, wait=1.5):
        pyperclip.copy(text)
        # 兼容不同系统的粘贴快捷键
        hotkey = 'command' if sys.platform == 'darwin' else 'ctrl'
        pyautogui.hotkey(hotkey, 'v')
        if press_enter:
            pyautogui.press('enter')
        time.sleep(wait)
        return f"Typed: {text}"

    def scroll(self, clicks, wait=1.5):
        pyautogui.scroll(clicks * 100)
        time.sleep(wait)
        return f"Scrolled {clicks}"

    def drag_mouse(self, start_x, start_y, end_x, end_y, duration=1.0):
        pyautogui.moveTo(start_x, start_y)
        pyautogui.dragTo(end_x, end_y, duration=duration)
        return f"Dragged from {start_x},{start_y} to {end_x},{end_y}"

    def press_key(self, key, wait=1.5):
        pyautogui.press(key)
        time.sleep(wait)
        return f"Pressed key: {key}"

    def hotkey(self, keys, wait=1.5):
        key_list = keys.split('+')
        pyautogui.hotkey(*key_list)
        time.sleep(wait)
        return f"Pressed hotkey: {keys}"

    # ---------------- WebSocket 基础维护 ----------------

    def connect(self):
        print(f"正在连接到 {self.url}...")
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.run_forever()

    def on_open(self, ws):
        self.is_connected = True
        print("✅ 连接成功！请输入指令或直接对话。")
        self.input_thread = threading.Thread(target=self.input_loop, daemon=True)
        self.input_thread.start()

    def send_message(self, text):
        """发送普通聊天消息"""
        payload = {
            "type": "chat",
            "data": text,
            "code": None,
            "callId": None
        }
        self.ws.send(json.dumps(payload))

    def on_error(self, ws, error):
        print(f"❌ WebSocket错误: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        self.is_connected = False
        print("🔌 连接已关闭")

    def input_loop(self):
        while self.running and self.is_connected:
            try:
                user_input = input("\033[96m>>> \033[0m").strip()
                if not user_input: continue
                if user_input.lower() in ['exit', 'quit']:
                    self.running = False
                    self.ws.close()
                    break
                self.send_message(user_input)
            except EOFError: break

if __name__ == "__main__":
    client = WebSocketClient("ws://localhost:8600/ws") # 替换为你的后端地址
    client.connect()
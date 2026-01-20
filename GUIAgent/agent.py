import time
import json
import base64
import traceback
from io import BytesIO

import numpy as np
import cv2
import mss
from PIL import Image

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.tools import tool

from tools import tools_list

# ================= 配置区域 =================
api_key = "sk-qpZdSlUmdbFnaF5WOWQ3tCTrqIzzYrDYBF8fmqOfJrdvpgaE"
base_url = "https://jeniya.top/v1"

system_prompt = """
# Role
You are an intelligent GUI Agent capable of performing multi-step tasks on a computer. 
You control the mouse and keyboard to achieve the user's high-level goals.

# Operational Space
- The screen coordinates are normalized to a 1000x1000 grid. 
- Top-left is (0,0), Bottom-right is (1000,1000).
- When you output coordinates for tools, use this 0-1000 scale. The system will automatically convert them to actual pixels.

# Workflow (ReAct Loop)
1. **Observe**: Analyze the provided screenshot.
2. **Reason**: 
   - Check if the user's goal is achieved.
   - If achieved, simply reply with a final text summary (do not call tools).
   - If not achieved, determine the NEXT single atomic action required.
3. **Act**: Call the appropriate tool.
4. **Wait**: The system will execute the tool and provide you with a new screenshot in the next turn.

# Rules
- **One Step at a Time**: Only call ONE tool per turn unless typing requires a click first.
- **Visual Grounding**: Look carefully at the UI elements. If you need to click an icon, estimate its center in the 1000x1000 grid.
- **Finish Condition**: When the task is done, output a text response telling the user it is complete. DO NOT call a tool if the task is done.
- **Retry**: If a step fails (e.g., menu didn't open), analyze the new screenshot and try a corrected action.
"""


def img2base64(image, max_size=1024):
    """将numpy数组图像转换为base64编码"""
    try:
        if isinstance(image, np.ndarray):
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(image.astype("uint8"))
        else:
            img = Image.open(image)

        if img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"[ERROR] img2base64: {str(e)}")
        raise


class ReActGUIAgent:
    def __init__(self, api_key, base_url, system_prompt):
        self.llm = ChatOpenAI(
            model="claude-sonnet-4-5-20250929",
            openai_api_key=api_key,
            base_url=base_url,
            temperature=0.1,
        )
        # 绑定工具
        self.llm_with_tools = self.llm.bind_tools(tools_list)
        self.system_prompt = system_prompt
        self.sct = mss.mss()

        # 获取屏幕实际分辨率用于坐标转换
        monitor = self.sct.monitors[1]
        self.screen_width = monitor["width"]
        self.screen_height = monitor["height"]
        print(f"[INFO] Screen resolution: {self.screen_width}x{self.screen_height}")

    def capture_screen(self):
        """截取当前屏幕"""
        screenshot = self.sct.grab(self.sct.monitors[1])
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

    def denormalize_coordinates(self, args):
        """将 0-1000 的归一化坐标转换为实际屏幕坐标"""
        new_args = args.copy()

        # 处理 x, y
        if "x" in new_args:
            new_args["x"] = int(new_args["x"] * self.screen_width / 1000)
        if "y" in new_args:
            new_args["y"] = int(new_args["y"] * self.screen_height / 1000)

        # 处理 start_x, start_y, end_x, end_y
        if "start_x" in new_args:
            new_args["start_x"] = int(new_args["start_x"] * self.screen_width / 1000)
        if "start_y" in new_args:
            new_args["start_y"] = int(new_args["start_y"] * self.screen_height / 1000)
        if "end_x" in new_args:
            new_args["end_x"] = int(new_args["end_x"] * self.screen_width / 1000)
        if "end_y" in new_args:
            new_args["end_y"] = int(new_args["end_y"] * self.screen_height / 1000)

        return new_args

    def run_task(self, goal):
        """运行一个ReAct循环直到任务完成"""
        print(f"\n[START] New Task: {goal}")

        # 初始化对话历史
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(
                content=f"Goal: {goal}. Please start by observing the screen."
            ),
        ]

        step_count = 0
        max_steps = 15

        while step_count < max_steps:
            step_count += 1
            print(f"\n--- Step {step_count} ---")

            # 1. 获取当前环境（截图）
            screen_img = self.capture_screen()
            b64_img = img2base64(screen_img)

            # 2. 构建当前轮次的输入消息

            current_turn_message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Here is the current screen state. What should we do next?",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                    },
                ]
            )

            # 发送给 LLM (历史 + 当前截图)
            try:
                response = self.llm_with_tools.invoke(messages + [current_turn_message])
            except Exception as e:
                print(f"[ERROR] LLM Invocation failed: {e}")
                break

            # 3. 处理 LLM 响应

            # 如果没有工具调用，说明 LLM 认为任务完成或需要提问
            if not response.tool_calls:
                print(f"[FINISH] Assistant: {response.content}")
                # 将最终回复加入历史（可选）
                messages.append(current_turn_message)
                messages.append(response)
                return response.content

            # 如果有工具调用，进入行动阶段
            print(f"[THOUGHT] Assistant: {response}")

            messages.append(HumanMessage(content="[Image of screen state]"))
            messages.append(response)

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                raw_args = tool_call["args"]
                call_id = tool_call["id"]

                print(f"[ACTION] Call: {tool_name} | Args (Normalized): {raw_args}")

                # 坐标转换 (0-1000 -> 实际分辨率)
                real_args = self.denormalize_coordinates(raw_args)

                # 执行工具
                # 查找对应的工具函数对象
                selected_tool = next(
                    (t for t in tools_list if t.name == tool_name), None
                )

                tool_output = "Error: Tool not found"
                if selected_tool:
                    try:
                        # LangChain tools 直接调用 invoke 或直接调用函数
                        # 这里直接调用函数逻辑，传入参数
                        tool_output = selected_tool.invoke(real_args)
                    except Exception as e:
                        tool_output = f"Error executing tool: {e}"

                print(f"[OBSERVATION] Result: {tool_output}")

                # 将工具执行结果反馈给 LLM
                messages.append(
                    ToolMessage(
                        tool_call_id=call_id, content=str(tool_output), name=tool_name
                    )
                )

            # 循环继续，下一轮会截取新图

        print("[WARN] Max steps reached.")
        return "Task stopped due to max steps limit."


if __name__ == "__main__":
    agent = ReActGUIAgent(api_key, base_url, system_prompt)

    while True:
        try:
            user_input = input("\nUser (type 'exit' to quit): ")
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input.strip():
                continue

            agent.run_task(user_input)

        except KeyboardInterrupt:
            print("\nUser interrupted.")
            break
        except Exception as e:
            print(f"Main Loop Error: {e}")
            traceback.print_exc()

import time
import base64
import io
import pyautogui
import pyperclip
from langchain_core.tools import tool

# 全局配置
scale = 1  # 如果是Retina屏幕可能需要设为2，普通屏幕设为1
pyautogui.PAUSE = 0.5
pyautogui.FAILSAFE = True

# ----------------- 辅助函数 -----------------

def _get_scaled_pos(x, y):
    """根据缩放比例计算实际坐标"""
    return x * scale, y * scale

# ----------------- LangChain Tools -----------------

@tool
def click_position(x: int, y: int, wait: float = 0.5):
    """
    点击屏幕上的指定位置 (x, y)。
    坐标必须是归一化后的坐标(0-1000)，不需要转换，外部调用者负责传入0-1000。
    
    *修改*: 为了配合Agent的逻辑，这里假设传入的是实际像素坐标。
    Agent层负责将 0-1000 映射回 实际分辨率。
    """
    try:
        real_x, real_y = _get_scaled_pos(x, y)
        pyautogui.moveTo(real_x, real_y, duration=0.3, tween=pyautogui.easeOutQuad)
        pyautogui.click()
        time.sleep(wait)
        return f"Clicked at ({x}, {y})"
    except Exception as e:
        return f"Error clicking: {str(e)}"

@tool
def double_click_position(x: int, y: int, wait: float = 0.5):
    """双击屏幕上的指定位置 (x, y)。"""
    try:
        real_x, real_y = _get_scaled_pos(x, y)
        pyautogui.moveTo(real_x, real_y, duration=0.3, tween=pyautogui.easeOutQuad)
        pyautogui.doubleClick()
        time.sleep(wait)
        return f"Double clicked at ({x}, {y})"
    except Exception as e:
        return f"Error double clicking: {str(e)}"

@tool
def right_click_position(x: int, y: int, wait: float = 0.5):
    """右键点击屏幕上的指定位置 (x, y)。"""
    try:
        real_x, real_y = _get_scaled_pos(x, y)
        pyautogui.moveTo(real_x, real_y, duration=0.3, tween=pyautogui.easeOutQuad)
        pyautogui.rightClick()
        time.sleep(wait)
        return f"Right clicked at ({x}, {y})"
    except Exception as e:
        return f"Error right clicking: {str(e)}"

@tool
def type_text(text: str, press_enter: bool = False, wait: float = 0.5):
    """
    输入文本。
    Args:
        text: 要输入的字符串
        press_enter: 输入完是否按回车
    """
    try:
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.1)
        if press_enter:
            pyautogui.press('enter')
        time.sleep(wait)
        return f"Typed text: '{text}'" + (" [Enter pressed]" if press_enter else "")
    except Exception as e:
        return f"Error typing: {str(e)}"

@tool
def scroll(clicks: int, wait: float = 0.5):
    """
    滚动鼠标滚轮。
    Args:
        clicks: 滚动的单位，正数向上，负数向下。
    """
    try:
        pyautogui.scroll(clicks * 100) # pyautogui的scroll单位通常比较小，乘以100放大效果
        time.sleep(wait)
        return f"Scrolled {clicks} units"
    except Exception as e:
        return f"Error scrolling: {str(e)}"

@tool
def drag_mouse(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 1.0):
    """
    拖拽鼠标。
    """
    try:
        sx, sy = _get_scaled_pos(start_x, start_y)
        ex, ey = _get_scaled_pos(end_x, end_y)
        pyautogui.moveTo(sx, sy)
        pyautogui.dragTo(ex, ey, duration=duration)
        return f"Dragged from ({start_x},{start_y}) to ({end_x},{end_y})"
    except Exception as e:
        return f"Error dragging: {str(e)}"

@tool
def press_key(key: str, wait: float = 0.5):
    """按下单个按键 (例如: 'enter', 'esc', 'space', 'backspace')."""
    try:
        pyautogui.press(key)
        time.sleep(wait)
        return f"Pressed key: {key}"
    except Exception as e:
        return f"Error pressing key: {str(e)}"

@tool
def hotkey(keys: str, wait: float = 0.5):
    """
    按下组合键。
    Args:
        keys: 组合键字符串，用加号连接，例如 'ctrl+c', 'alt+tab'
    """
    try:
        key_list = keys.split('+')
        pyautogui.hotkey(*key_list)
        time.sleep(wait)
        return f"Pressed hotkey: {keys}"
    except Exception as e:
        return f"Error pressing hotkey: {str(e)}"

# 导出工具列表
tools_list = [
    click_position,
    double_click_position,
    right_click_position,
    type_text,
    scroll,
    drag_mouse,
    press_key,
    hotkey
]
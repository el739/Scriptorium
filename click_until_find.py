import pyautogui
import time
import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL('user32', use_last_error=True)
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

# VK_SPACE 是空格键的虚拟键码
VK_SPACE = 0x20

class KEYBDINPUT(ctypes.Structure):
    _fields_ = (("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)))

class INPUT(ctypes.Structure):
    _fields_ = (("type", wintypes.DWORD),
                ("ki", KEYBDINPUT),
                ("padding", ctypes.c_ubyte * 8))

def find_image_on_screen(image_path, confidence=0.8):
    """在屏幕上查找指定图像"""
    try:
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
        if location:
            print(f"找到图像 {image_path}，位置: {location}")
            return True
        return False
    except Exception as e:
        print(f"查找图像时出错: {e}")
        return False

def press_space_low_level():
    """使用低级Windows API按下空格键"""
    # 创建按下空格键的输入
    x = INPUT(type=INPUT_KEYBOARD, 
              ki=KEYBDINPUT(wVk=VK_SPACE, 
                           wScan=0,
                           dwFlags=0,
                           time=0,
                           dwExtraInfo=ctypes.pointer(ctypes.c_ulong(0))))
    
    # 创建释放空格键的输入
    y = INPUT(type=INPUT_KEYBOARD, 
              ki=KEYBDINPUT(wVk=VK_SPACE, 
                           wScan=0,
                           dwFlags=KEYEVENTF_KEYUP,
                           time=0,
                           dwExtraInfo=ctypes.pointer(ctypes.c_ulong(0))))
    
    # 发送输入
    user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))
    time.sleep(0.05)  # 短暂延迟
    user32.SendInput(1, ctypes.byref(y), ctypes.sizeof(y))

def main():
    image_path = "image.png"
    search_interval = 0.01
    
    print(f"开始寻找图像: {image_path}")
    print("按 Ctrl+C 停止脚本")
    
    try:
        while True:
            if find_image_on_screen(image_path):
                print("成功找到图像！停止搜索。")
                break
            else:
                print("未找到图像，按下空格键...")
                press_space_low_level()
                time.sleep(search_interval)
    
    except KeyboardInterrupt:
        print("用户中断了脚本")

if __name__ == "__main__":
    print("脚本将在3秒后开始运行...")
    time.sleep(3)
    main()

import sys
import time
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from pynput import mouse, keyboard

# 后台点击线程
class ClickerThread(QThread):
    status_changed = pyqtSignal(str)

    def __init__(self, key_to_press):
        super().__init__()
        self.key_to_press = key_to_press
        self.is_running = True
        self.is_clicking = False
        self.mouse_controller = mouse.Controller()

    def run(self):
        """
        在线程中运行键盘监听器。
        """
        self.status_changed.emit(f"正在运行... 按下 '{self.key_to_press}' 键开始点击")
        
        # 定义按键事件处理函数
        def on_press(key):
            try:
                # 检查按下的键是否是目标键
                if key == self.key_to_press:
                    self.is_clicking = True
            except AttributeError:
                pass # 忽略特殊按键的错误

        def on_release(key):
            try:
                if key == self.key_to_press:
                    self.is_clicking = False
            except AttributeError:
                pass

        # 创建并启动键盘监听器
        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()

        # 循环检查是否需要点击
        while self.is_running:
            if self.is_clicking:
                self.mouse_controller.click(mouse.Button.left)
                time.sleep(0.01) # 控制点击速度，可以根据需要调整
            else:
                time.sleep(0.01) # 避免CPU占用过高

        self.listener.stop()
        self.status_changed.emit("已停止")

    def stop(self):
        """
        停止线程和监听器。
        """
        self.is_running = False
        self.is_clicking = False


# 主窗口
class AutoClickerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("自动点击器")
        self.setGeometry(300, 300, 300, 150)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # --- UI 元素 ---
        self.status_label = QLabel("请先设置一个热键")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.key_layout = QHBoxLayout()
        self.key_label = QLabel("当前热键:")
        self.selected_key_label = QLabel("未设置")
        self.key_layout.addWidget(self.key_label)
        self.key_layout.addWidget(self.selected_key_label)

        self.set_key_button = QPushButton("设置热键")
        self.start_button = QPushButton("开始")
        self.stop_button = QPushButton("停止")

        # --- 初始化状态 ---
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.selected_key = None
        self.clicker_thread = None

        # --- 添加到布局 ---
        self.layout.addWidget(self.status_label)
        self.layout.addLayout(self.key_layout)
        self.layout.addWidget(self.set_key_button)
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.stop_button)

        # --- 连接信号和槽 ---
        self.set_key_button.clicked.connect(self.set_key_mode)
        self.start_button.clicked.connect(self.start_clicking)
        self.stop_button.clicked.connect(self.stop_clicking)

    def set_key_mode(self):
        """
        进入按键设置模式，等待用户按键。
        """
        self.set_key_button.setText("请按下一个键...")
        self.set_key_button.setEnabled(False)
        self.grabKeyboard() # 捕获键盘输入

    def keyPressEvent(self, event):
        """
        捕获按键事件以设置热键。
        """
        if self.set_key_button.text() == "请按下一个键...":
            key_code = event.key()
            
            # 尝试将按键代码转换为字符
            try:
                # 处理普通按键
                self.selected_key = keyboard.KeyCode.from_char(chr(key_code).lower())
                key_name = chr(key_code).lower()
            except (ValueError, TypeError):
                 # 处理特殊按键 (e.g., Ctrl, Alt, F1-F12)
                qt_key_map = {
                    Qt.Key.Key_Control: keyboard.Key.ctrl,
                    Qt.Key.Key_Alt: keyboard.Key.alt,
                    Qt.Key.Key_Shift: keyboard.Key.shift,
                    Qt.Key.Key_Meta: keyboard.Key.cmd,
                    Qt.Key.Key_F1: keyboard.Key.f1,
                    Qt.Key.Key_F2: keyboard.Key.f2,
                    Qt.Key.Key_F3: keyboard.Key.f3,
                    Qt.Key.Key_F4: keyboard.Key.f4,
                    Qt.Key.Key_F5: keyboard.Key.f5,
                    Qt.Key.Key_F6: keyboard.Key.f6,
                    Qt.Key.Key_F7: keyboard.Key.f7,
                    Qt.Key.Key_F8: keyboard.Key.f8,
                    Qt.Key.Key_F9: keyboard.Key.f9,
                    Qt.Key.Key_F10: keyboard.Key.f10,
                    Qt.Key.Key_F11: keyboard.Key.f11,
                    Qt.Key.Key_F12: keyboard.Key.f12,
                    Qt.Key.Key_Space: keyboard.Key.space,
                }
                if key_code in qt_key_map:
                    self.selected_key = qt_key_map[key_code]
                    key_name = self.selected_key.name
                else:
                    key_name = "未知按键"
                    self.selected_key = None

            if self.selected_key:
                self.selected_key_label.setText(f"'{key_name}'")
                self.status_label.setText("热键已设置，可以开始了")
                self.start_button.setEnabled(True)

            self.set_key_button.setText("设置热键")
            self.set_key_button.setEnabled(True)
            self.releaseKeyboard() # 释放键盘捕获

    def start_clicking(self):
        """
        启动点击线程。
        """
        if not self.selected_key:
            self.status_label.setText("错误：请先设置一个有效的热键")
            return

        self.clicker_thread = ClickerThread(self.selected_key)
        self.clicker_thread.status_changed.connect(self.status_label.setText)
        self.clicker_thread.start()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.set_key_button.setEnabled(False)

    def stop_clicking(self):
        """
        停止点击线程。
        """
        if self.clicker_thread:
            self.clicker_thread.stop()
            self.clicker_thread.wait() # 等待线程完全结束

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.set_key_button.setEnabled(True)
        self.status_label.setText("已停止。可以重新开始或设置新热键。")

    def closeEvent(self, event):
        """
        确保在关闭窗口时停止线程。
        """
        self.stop_clicking()
        event.accept()


if __name__ == "__main__":
    # 确保在不同操作系统上高DPI缩放正常
    #QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    window = AutoClickerWindow()
    window.show()
    sys.exit(app.exec())

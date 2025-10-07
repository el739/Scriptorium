import sys
import os
import chardet
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QComboBox, QTextEdit, 
                             QFileDialog, QMessageBox, QProgressBar, QGroupBox,
                             QGridLayout, QLineEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

class EncodingConverter(QThread):
    """编码转换工作线程"""
    progress_updated = pyqtSignal(int)
    conversion_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, input_file, output_file, source_encoding, target_encoding):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.source_encoding = source_encoding
        self.target_encoding = target_encoding
    
    def run(self):
        try:
            # 读取原文件
            self.progress_updated.emit(20)
            with open(self.input_file, 'r', encoding=self.source_encoding) as f:
                content = f.read()
            
            self.progress_updated.emit(60)
            
            # 写入新文件
            with open(self.output_file, 'w', encoding=self.target_encoding) as f:
                f.write(content)
            
            self.progress_updated.emit(100)
            self.conversion_finished.emit(f"转换成功！文件已保存到：{self.output_file}")
            
        except UnicodeDecodeError as e:
            self.error_occurred.emit(f"源编码解码错误：{str(e)}")
        except UnicodeEncodeError as e:
            self.error_occurred.emit(f"目标编码编码错误：{str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"转换失败：{str(e)}")

class EncodingConverterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.input_file_path = ""
        self.output_file_path = ""
        self.conversion_thread = None
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("文本文件编码转换器")
        self.setGeometry(300, 300, 600, 500)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 标题
        title_label = QLabel("文本文件编码转换器")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        main_layout.addWidget(title_label)
        
        # 文件选择组
        file_group = QGroupBox("文件选择")
        file_layout = QGridLayout()
        file_group.setLayout(file_layout)
        
        # 输入文件
        file_layout.addWidget(QLabel("输入文件:"), 0, 0)
        self.input_file_edit = QLineEdit()
        self.input_file_edit.setReadOnly(True)
        file_layout.addWidget(self.input_file_edit, 0, 1)
        
        self.browse_input_btn = QPushButton("浏览...")
        self.browse_input_btn.clicked.connect(self.browse_input_file)
        file_layout.addWidget(self.browse_input_btn, 0, 2)
        
        # 输出文件
        file_layout.addWidget(QLabel("输出文件:"), 1, 0)
        self.output_file_edit = QLineEdit()
        file_layout.addWidget(self.output_file_edit, 1, 1)
        
        self.browse_output_btn = QPushButton("浏览...")
        self.browse_output_btn.clicked.connect(self.browse_output_file)
        file_layout.addWidget(self.browse_output_btn, 1, 2)
        
        main_layout.addWidget(file_group)
        
        # 编码选择组
        encoding_group = QGroupBox("编码设置")
        encoding_layout = QGridLayout()
        encoding_group.setLayout(encoding_layout)
        
        # 常见编码列表
        encodings = ['auto-detect', 'utf-8', 'gb2312', 'gbk', 'big5', 'ascii', 
                    'iso-8859-1', 'utf-16', 'utf-32', 'cp1252']
        
        # 源编码
        encoding_layout.addWidget(QLabel("源编码:"), 0, 0)
        self.source_encoding_combo = QComboBox()
        self.source_encoding_combo.addItems(encodings)
        self.source_encoding_combo.setCurrentText('auto-detect')
        encoding_layout.addWidget(self.source_encoding_combo, 0, 1)
        
        # 目标编码
        encoding_layout.addWidget(QLabel("目标编码:"), 1, 0)
        self.target_encoding_combo = QComboBox()
        self.target_encoding_combo.addItems(encodings[1:])  # 排除auto-detect
        self.target_encoding_combo.setCurrentText('utf-8')
        encoding_layout.addWidget(self.target_encoding_combo, 1, 1)
        
        # 检测编码按钮
        self.detect_btn = QPushButton("自动检测源编码")
        self.detect_btn.clicked.connect(self.detect_encoding)
        encoding_layout.addWidget(self.detect_btn, 0, 2)
        
        main_layout.addWidget(encoding_group)
        
        # 预览区域
        preview_group = QGroupBox("文件预览")
        preview_layout = QVBoxLayout()
        preview_group.setLayout(preview_layout)
        
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(150)
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)
        
        main_layout.addWidget(preview_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 转换按钮
        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; }")
        main_layout.addWidget(self.convert_btn)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
    def browse_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择输入文件", "", "文本文件 (*.txt);;所有文件 (*)")
        
        if file_path:
            self.input_file_path = file_path
            self.input_file_edit.setText(file_path)
            
            # 自动设置输出文件名
            if not self.output_file_edit.text():
                dir_name = os.path.dirname(file_path)
                file_name = os.path.basename(file_path)
                name, ext = os.path.splitext(file_name)
                output_file = os.path.join(dir_name, f"{name}_converted{ext}")
                self.output_file_edit.setText(output_file)
            
            # 预览文件内容
            self.preview_file()
    
    def browse_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择输出文件", "", "文本文件 (*.txt);;所有文件 (*)")
        
        if file_path:
            self.output_file_path = file_path
            self.output_file_edit.setText(file_path)
    
    def detect_encoding(self):
        if not self.input_file_path:
            QMessageBox.warning(self, "警告", "请先选择输入文件！")
            return
        
        try:
            with open(self.input_file_path, 'rb') as f:
                raw_data = f.read(10000)  # 读取前10000字节进行检测
            
            result = chardet.detect(raw_data)
            detected_encoding = result['encoding']
            confidence = result['confidence']
            
            if detected_encoding:
                # 设置检测到的编码
                self.source_encoding_combo.setCurrentText(detected_encoding.lower())
                self.status_label.setText(f"检测到编码: {detected_encoding} (置信度: {confidence:.2%})")
            else:
                self.status_label.setText("无法检测编码")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编码检测失败：{str(e)}")
    
    def preview_file(self):
        if not self.input_file_path:
            return
        
        try:
            # 尝试用当前选择的编码读取文件
            encoding = self.source_encoding_combo.currentText()
            if encoding == 'auto-detect':
                # 自动检测编码
                with open(self.input_file_path, 'rb') as f:
                    raw_data = f.read(1000)
                result = chardet.detect(raw_data)
                encoding = result['encoding'] or 'utf-8'
            
            with open(self.input_file_path, 'r', encoding=encoding) as f:
                content = f.read(500)  # 只读取前500个字符进行预览
            
            self.preview_text.setPlainText(content + "\n...(预览前500字符)")
            
        except Exception as e:
            self.preview_text.setPlainText(f"预览失败：{str(e)}")
    
    def start_conversion(self):
        # 验证输入
        if not self.input_file_path:
            QMessageBox.warning(self, "警告", "请选择输入文件！")
            return
        
        output_file = self.output_file_edit.text()
        if not output_file:
            QMessageBox.warning(self, "警告", "请设置输出文件路径！")
            return
        
        source_encoding = self.source_encoding_combo.currentText()
        target_encoding = self.target_encoding_combo.currentText()
        
        if source_encoding == target_encoding:
            QMessageBox.information(self, "提示", "源编码和目标编码相同，无需转换！")
            return
        
        # 处理自动检测编码
        if source_encoding == 'auto-detect':
            try:
                with open(self.input_file_path, 'rb') as f:
                    raw_data = f.read(10000)
                result = chardet.detect(raw_data)
                source_encoding = result['encoding']
                if not source_encoding:
                    QMessageBox.critical(self, "错误", "无法自动检测源文件编码！")
                    return
            except Exception as e:
                QMessageBox.critical(self, "错误", f"编码检测失败：{str(e)}")
                return
        
        # 开始转换
        self.convert_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在转换...")
        
        # 创建转换线程
        self.conversion_thread = EncodingConverter(
            self.input_file_path, output_file, source_encoding, target_encoding)
        
        # 连接信号
        self.conversion_thread.progress_updated.connect(self.progress_bar.setValue)
        self.conversion_thread.conversion_finished.connect(self.on_conversion_finished)
        self.conversion_thread.error_occurred.connect(self.on_conversion_error)
        
        # 启动线程
        self.conversion_thread.start()
    
    def on_conversion_finished(self, message):
        self.status_label.setText(message)
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)
        QMessageBox.information(self, "成功", message)
    
    def on_conversion_error(self, error_message):
        self.status_label.setText(f"转换失败：{error_message}")
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)
        QMessageBox.critical(self, "转换失败", error_message)

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = EncodingConverterGUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox, 
                             QFileDialog, QProgressBar, QMessageBox, QSpinBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import fitz  # PyMuPDF
from PIL import Image
import os


class PDFProcessThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, pdf_path, layout, dpi, output_dir=None):
        super().__init__()
        self.pdf_path = pdf_path
        self.layout = layout
        self.dpi = dpi
        
        # 如果没有指定输出目录，使用PDF文件所在目录
        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = os.path.dirname(pdf_path)
        
        # 获取PDF文件名（不含扩展名）
        self.base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
    def run(self):
        try:
            # 打开PDF
            doc = fitz.open(self.pdf_path)
            total_pages = len(doc)
            
            # 根据布局确定每张图片包含的页数
            layout_map = {'2x2': 4, '3x2': 6, '3x3': 9}
            pages_per_image = layout_map[self.layout]
            
            # 计算行列数
            if self.layout == '2x2':
                rows, cols = 2, 2
            elif self.layout == '3x2':
                rows, cols = 3, 2
            else:  # 3x3
                rows, cols = 3, 3
            
            # 渲染所有页面为图片
            page_images = []
            for i in range(total_pages):
                page = doc[i]
                mat = fitz.Matrix(self.dpi/72, self.dpi/72)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_images.append(img)
                self.progress.emit(int((i + 1) / total_pages * 50))
            
            # 获取单页尺寸
            if page_images:
                page_width, page_height = page_images[0].size
            else:
                raise Exception("PDF没有页面")
            
            # 创建合并图片
            output_count = 0
            for start_idx in range(0, total_pages, pages_per_image):
                # 创建画布
                canvas_width = page_width * cols
                canvas_height = page_height * rows
                canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
                
                # 粘贴页面
                for i in range(pages_per_image):
                    page_idx = start_idx + i
                    if page_idx >= total_pages:
                        break
                    
                    row = i // cols
                    col = i % cols
                    x = col * page_width
                    y = row * page_height
                    
                    canvas.paste(page_images[page_idx], (x, y))
                
                # 保存图片
                output_count += 1
                output_path = os.path.join(self.output_dir, f'{self.base_name}_merged_{output_count}.png')
                canvas.save(output_path, 'PNG', quality=95)
                
                progress_val = 50 + int((start_idx + pages_per_image) / total_pages * 50)
                self.progress.emit(min(progress_val, 100))
            
            doc.close()
            self.finished.emit(f"成功生成 {output_count} 张图片\n保存位置: {self.output_dir}")
            
        except Exception as e:
            self.error.emit(str(e))


class PDFMergerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pdf_path = None
        self.output_dir = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('PDF页面聚合工具')
        self.setGeometry(100, 100, 600, 350)
        
        # 主widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel('PDF页面聚合工具')
        title.setFont(QFont('Arial', 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # PDF文件选择
        pdf_layout = QHBoxLayout()
        self.pdf_label = QLabel('未选择PDF文件')
        self.pdf_label.setStyleSheet('padding: 8px; background: #f0f0f0; border-radius: 4px;')
        pdf_btn = QPushButton('选择PDF')
        pdf_btn.clicked.connect(self.select_pdf)
        pdf_layout.addWidget(self.pdf_label, 3)
        pdf_layout.addWidget(pdf_btn, 1)
        layout.addLayout(pdf_layout)
        
        # 输出目录选择（可选）
        output_layout = QHBoxLayout()
        self.output_label = QLabel('默认保存到PDF文件所在目录')
        self.output_label.setStyleSheet('padding: 8px; background: #e8f5e9; border-radius: 4px;')
        output_btn = QPushButton('自定义输出目录')
        output_btn.clicked.connect(self.select_output)
        output_layout.addWidget(self.output_label, 3)
        output_layout.addWidget(output_btn, 1)
        layout.addLayout(output_layout)
        
        # 布局选择
        layout_h = QHBoxLayout()
        layout_h.addWidget(QLabel('页面布局:'))
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(['2x2 (4页)', '3x2 (6页)', '3x3 (9页)'])
        layout_h.addWidget(self.layout_combo)
        layout_h.addStretch()
        layout.addLayout(layout_h)
        
        # DPI设置
        dpi_layout = QHBoxLayout()
        dpi_layout.addWidget(QLabel('图片DPI:'))
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(150)
        self.dpi_spin.setSuffix(' dpi')
        dpi_layout.addWidget(self.dpi_spin)
        dpi_layout.addStretch()
        layout.addLayout(dpi_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 转换按钮
        self.convert_btn = QPushButton('开始转换')
        self.convert_btn.setStyleSheet('''
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        ''')
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setEnabled(False)
        layout.addWidget(self.convert_btn)
        
        # 状态标签
        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('color: #666; font-style: italic;')
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
    def select_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, '选择PDF文件', '', 'PDF文件 (*.pdf)'
        )
        if file_path:
            self.pdf_path = file_path
            self.pdf_label.setText(os.path.basename(file_path))
            
            # 自动设置输出目录为PDF所在目录
            self.output_dir = None  # 重置为None，表示使用默认位置
            pdf_dir = os.path.dirname(file_path)
            self.output_label.setText(f'输出到: {pdf_dir}')
            self.output_label.setStyleSheet('padding: 8px; background: #e8f5e9; border-radius: 4px;')
            
            self.check_ready()
            
    def select_output(self):
        dir_path = QFileDialog.getExistingDirectory(self, '选择输出目录')
        if dir_path:
            self.output_dir = dir_path
            self.output_label.setText(f'自定义输出: {dir_path}')
            self.output_label.setStyleSheet('padding: 8px; background: #fff3e0; border-radius: 4px;')
            self.check_ready()
            
    def check_ready(self):
        # 只要选择了PDF文件就可以转换
        if self.pdf_path:
            self.convert_btn.setEnabled(True)
            self.status_label.setText('准备就绪')
        
    def start_conversion(self):
        # 获取布局设置
        layout_text = self.layout_combo.currentText()
        layout = layout_text.split()[0]  # 提取 "2x2", "3x2", "3x3"
        
        # 获取DPI
        dpi = self.dpi_spin.value()
        
        # 禁用按钮，显示进度条
        self.convert_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText('处理中...')
        
        # 创建处理线程（如果output_dir为None，线程会自动使用PDF所在目录）
        self.thread = PDFProcessThread(self.pdf_path, layout, dpi, self.output_dir)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.conversion_finished)
        self.thread.error.connect(self.conversion_error)
        self.thread.start()
        
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def conversion_finished(self, message):
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.status_label.setText('转换完成')
        QMessageBox.information(self, '完成', message)
        
    def conversion_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.status_label.setText('转换失败')
        QMessageBox.critical(self, '错误', f'转换失败: {error_msg}')


def main():
    app = QApplication(sys.argv)
    window = PDFMergerGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
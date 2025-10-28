import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QFileDialog, QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt
from PyPDF2 import PdfReader, PdfWriter
import os


class PDFSplitterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pdf_path = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('PDF 分页工具')
        self.setGeometry(100, 100, 600, 400)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        layout = QVBoxLayout()
        
        # 文件选择部分
        file_layout = QHBoxLayout()
        self.file_label = QLabel('未选择文件')
        self.file_label.setStyleSheet('padding: 5px; background-color: #f0f0f0;')
        select_btn = QPushButton('选择PDF文件')
        select_btn.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_label, stretch=1)
        file_layout.addWidget(select_btn)
        
        # 分页规则输入
        rule_layout = QVBoxLayout()
        rule_label = QLabel('分页规则 (例如: 1-5,6,7-9):')
        rule_label.setStyleSheet('font-weight: bold; margin-top: 10px;')
        self.rule_input = QLineEdit()
        self.rule_input.setPlaceholderText('输入页码范围，用逗号分隔...')
        
        # 说明文本
        help_text = QLabel(
            '说明：\n'
            '• 单页: 6\n'
            '• 页码范围: 1-5\n'
            '• 多个部分用逗号分隔: 1-5,6,7-9\n'
            '• 这将生成3个PDF文件'
        )
        help_text.setStyleSheet('color: #666; font-size: 11px; padding: 5px;')
        
        rule_layout.addWidget(rule_label)
        rule_layout.addWidget(self.rule_input)
        rule_layout.addWidget(help_text)
        
        # 输出目录选择
        output_layout = QHBoxLayout()
        output_label = QLabel('输出目录:')
        output_label.setStyleSheet('font-weight: bold; margin-top: 10px;')
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText('选择输出目录 (默认为PDF所在目录)')
        output_btn = QPushButton('选择目录')
        output_btn.clicked.connect(self.select_output_dir)
        
        output_layout.addWidget(self.output_path, stretch=1)
        output_layout.addWidget(output_btn)
        
        # 执行按钮
        execute_btn = QPushButton('开始分割')
        execute_btn.setStyleSheet(
            'QPushButton {'
            '    background-color: #4CAF50;'
            '    color: white;'
            '    padding: 10px;'
            '    font-size: 14px;'
            '    font-weight: bold;'
            '    border-radius: 5px;'
            '}'
            'QPushButton:hover {'
            '    background-color: #45a049;'
            '}'
        )
        execute_btn.clicked.connect(self.split_pdf)
        
        # 日志输出
        log_label = QLabel('执行日志:')
        log_label.setStyleSheet('font-weight: bold; margin-top: 10px;')
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        
        # 添加所有组件到主布局
        layout.addLayout(file_layout)
        layout.addLayout(rule_layout)
        layout.addWidget(output_label)
        layout.addLayout(output_layout)
        layout.addWidget(execute_btn)
        layout.addWidget(log_label)
        layout.addWidget(self.log_text)
        
        central_widget.setLayout(layout)
        
    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, '选择PDF文件', '', 'PDF Files (*.pdf)'
        )
        if file_path:
            self.pdf_path = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.log(f'已选择文件: {file_path}')
            
    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, '选择输出目录')
        if dir_path:
            self.output_path.setText(dir_path)
            self.log(f'输出目录: {dir_path}')
            
    def log(self, message):
        self.log_text.append(message)
        
    def parse_page_ranges(self, rule_string):
        """解析页码范围字符串，返回页码范围列表"""
        ranges = []
        parts = rule_string.replace(' ', '').split(',')
        
        for part in parts:
            if '-' in part:
                start, end = part.split('-')
                ranges.append((int(start), int(end)))
            else:
                page = int(part)
                ranges.append((page, page))
                
        return ranges
        
    def split_pdf(self):
        # 验证输入
        if not self.pdf_path:
            QMessageBox.warning(self, '错误', '请先选择PDF文件！')
            return
            
        rule_string = self.rule_input.text().strip()
        if not rule_string:
            QMessageBox.warning(self, '错误', '请输入分页规则！')
            return
            
        try:
            # 解析分页规则
            ranges = self.parse_page_ranges(rule_string)
            self.log(f'\n开始分割PDF，共 {len(ranges)} 个部分...')
            
            # 读取PDF
            reader = PdfReader(self.pdf_path)
            total_pages = len(reader.pages)
            self.log(f'PDF总页数: {total_pages}')
            
            # 确定输出目录
            output_dir = self.output_path.text().strip()
            if not output_dir:
                output_dir = os.path.dirname(self.pdf_path)
                
            base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
            
            # 分割PDF
            for idx, (start, end) in enumerate(ranges, 1):
                # 验证页码范围
                if start < 1 or end > total_pages:
                    self.log(f'警告: 范围 {start}-{end} 超出页码范围，跳过')
                    continue
                    
                writer = PdfWriter()
                
                # 添加页面 (PyPDF2使用0索引)
                for page_num in range(start - 1, end):
                    writer.add_page(reader.pages[page_num])
                
                # 保存文件
                output_file = os.path.join(
                    output_dir, 
                    f'{base_name}_part{idx}_pages{start}-{end}.pdf'
                )
                
                with open(output_file, 'wb') as f:
                    writer.write(f)
                
                self.log(f'✓ 已保存: {os.path.basename(output_file)} (页 {start}-{end})')
            
            self.log('\n分割完成！')
            QMessageBox.information(self, '成功', f'PDF分割完成！\n共生成 {len(ranges)} 个文件。')
            
        except ValueError as e:
            QMessageBox.critical(self, '错误', f'分页规则格式错误: {e}')
            self.log(f'错误: 分页规则格式错误 - {e}')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'处理失败: {e}')
            self.log(f'错误: {e}')


def main():
    app = QApplication(sys.argv)
    window = PDFSplitterGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
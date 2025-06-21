import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from pypdf import PdfReader, PdfWriter

class PDFSplitterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF 页面提取器 (PDF Page Extractor)")
        self.setGeometry(100, 100, 550, 280) # x, y, width, height

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10) # 设置控件间的间距
        layout.setContentsMargins(10, 10, 10, 10) # 设置窗口边距

        # --- Input PDF ---
        input_group_layout = QHBoxLayout()
        self.input_pdf_label = QLabel("输入 PDF:")
        self.input_pdf_path_edit = QLineEdit()
        self.input_pdf_path_edit.setPlaceholderText("请选择一个 PDF 文件")
        self.input_pdf_path_edit.setReadOnly(True)
        self.browse_input_button = QPushButton("浏览...")
        self.browse_input_button.clicked.connect(self.browse_input_pdf)
        
        input_group_layout.addWidget(self.input_pdf_label)
        input_group_layout.addWidget(self.input_pdf_path_edit, 1) # 让输入框占据更多空间
        input_group_layout.addWidget(self.browse_input_button)
        layout.addLayout(input_group_layout)

        # --- Page Range ---
        page_range_layout = QHBoxLayout()
        self.page_range_label = QLabel("页面范围:")
        self.page_range_edit = QLineEdit()
        self.page_range_edit.setPlaceholderText("例如: 5-10, 12, 15-17 (1-indexed)")
        
        page_range_layout.addWidget(self.page_range_label)
        page_range_layout.addWidget(self.page_range_edit, 1)
        layout.addLayout(page_range_layout)

        # --- Output PDF ---
        output_group_layout = QHBoxLayout()
        self.output_pdf_label = QLabel("输出 PDF:")
        self.output_pdf_path_edit = QLineEdit()
        self.output_pdf_path_edit.setPlaceholderText("请选择保存位置和文件名")
        self.output_pdf_path_edit.setReadOnly(True)
        self.browse_output_button = QPushButton("浏览...")
        self.browse_output_button.clicked.connect(self.browse_output_pdf)

        output_group_layout.addWidget(self.output_pdf_label)
        output_group_layout.addWidget(self.output_pdf_path_edit, 1)
        output_group_layout.addWidget(self.browse_output_button)
        layout.addLayout(output_group_layout)

        # --- Extract Button ---
        self.extract_button = QPushButton("📄 提取页面")
        self.extract_button.setFixedHeight(40) # 使得按钮更显眼
        self.extract_button.clicked.connect(self.extract_pages)
        layout.addWidget(self.extract_button)

        # --- Status Label ---
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: gray;") # 初始颜色
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def browse_input_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择输入 PDF", "", "PDF 文件 (*.pdf)")
        if file_path:
            self.input_pdf_path_edit.setText(file_path)
            self.status_label.setText("") # 清除旧状态

    def browse_output_pdf(self):
        default_input_path = self.input_pdf_path_edit.text()
        default_dir = ""
        default_filename = "extracted_pages.pdf"
        if default_input_path:
            import os
            default_dir = os.path.dirname(default_input_path)
            base_name = os.path.basename(default_input_path)
            name_part, ext_part = os.path.splitext(base_name)
            default_filename = f"{name_part}_extracted{ext_part}"


        file_path, _ = QFileDialog.getSaveFileName(self, "保存输出 PDF", os.path.join(default_dir, default_filename) if default_dir else default_filename, "PDF 文件 (*.pdf)")
        if file_path:
            if not file_path.lower().endswith(".pdf"):
                file_path += ".pdf"
            self.output_pdf_path_edit.setText(file_path)
            self.status_label.setText("") # 清除旧状态

    def parse_page_ranges(self, range_str, max_pages):
        """
        将页面范围字符串 (例如 "1-3,5,7-9") 解析为 0-indexed 的页面编号列表。
        用户输入是 1-indexed。
        """
        pages_to_extract = set()
        if not range_str.strip():
            raise ValueError("页面范围不能为空。")

        parts = range_str.split(',')
        for part in parts:
            part = part.strip()
            if not part: # 跳过空的部分，比如 "1,,2" 中的第二个逗号
                continue
            
            if '-' in part:
                try:
                    start_str, end_str = part.split('-', 1)
                    start_str, end_str = start_str.strip(), end_str.strip()
                    if not start_str.isdigit() or not end_str.isdigit():
                        raise ValueError(f"范围 '{part}' 中包含非数字字符。")
                    
                    start_page = int(start_str)
                    end_page = int(end_str)
                except ValueError: # 捕获 split 可能失败的情况，或 int 转换失败
                     raise ValueError(f"无效的范围格式: '{part}'。请使用 '数字-数字' 格式。")

                if start_page <= 0 or end_page <= 0:
                    raise ValueError(f"页码必须为正数: '{part}'。")
                if start_page > end_page:
                    raise ValueError(f"范围起始页码 '{start_page}' 不能大于结束页码 '{end_page}'。")
                if end_page > max_pages:
                    raise ValueError(f"请求的页面 {end_page} 超出文档总页数 {max_pages} (文档共 {max_pages} 页)。")
                
                for i in range(start_page, end_page + 1):
                    pages_to_extract.add(i - 1) # 转换为 0-indexed
            else:
                if not part.isdigit():
                    raise ValueError(f"无效的页码格式: '{part}'。请使用数字。")
                page = int(part)
                if page <= 0:
                    raise ValueError(f"页码必须为正数: '{part}'。")
                if page > max_pages:
                     raise ValueError(f"请求的页面 {page} 超出文档总页数 {max_pages} (文档共 {max_pages} 页)。")
                pages_to_extract.add(page - 1) # 转换为 0-indexed
        
        if not pages_to_extract:
             raise ValueError("未能解析出有效的页面范围，或所有指定页面均无效。")
             
        return sorted(list(pages_to_extract))


    def extract_pages(self):
        input_pdf_path = self.input_pdf_path_edit.text()
        page_range_str = self.page_range_edit.text()
        output_pdf_path = self.output_pdf_path_edit.text()

        if not input_pdf_path:
            QMessageBox.warning(self, "⚠️ 输入错误", "请选择输入 PDF 文件。")
            return
        if not page_range_str:
            QMessageBox.warning(self, "⚠️ 输入错误", "请输入页面范围。")
            return
        if not output_pdf_path:
            QMessageBox.warning(self, "⚠️ 输入错误", "请选择输出 PDF 文件路径。")
            return

        try:
            self.status_label.setText("⚙️ 正在处理...")
            self.status_label.setStyleSheet("color: orange;")
            QApplication.processEvents() 

            reader = PdfReader(input_pdf_path)
            writer = PdfWriter()
            total_pages_in_pdf = len(reader.pages)

            if total_pages_in_pdf == 0:
                QMessageBox.information(self, "ℹ️ 信息", "输入的 PDF 文件不包含任何页面。")
                self.status_label.setText("输入 PDF 为空")
                self.status_label.setStyleSheet("color: gray;")
                return

            pages_to_extract_0_indexed = self.parse_page_ranges(page_range_str, total_pages_in_pdf)
            
            for page_idx in pages_to_extract_0_indexed:
                # parse_page_ranges 已经检查过 page_idx < total_pages_in_pdf
                writer.add_page(reader.pages[page_idx])

            if len(writer.pages) == 0:
                 QMessageBox.information(self, "ℹ️ 信息", "没有页面被提取。请检查您的页面范围输入是否有效且在文档范围内。")
                 self.status_label.setText("完成，但未提取页面。")
                 self.status_label.setStyleSheet("color: gray;")
                 return

            with open(output_pdf_path, "wb") as output_file:
                writer.write(output_file)

            self.status_label.setText(f"✅ 完成！已保存 {len(writer.pages)} 页到指定路径。")
            self.status_label.setStyleSheet("color: green;")
            QMessageBox.information(self, "🎉 成功", f"PDF 页面已成功提取并保存到:\n{output_pdf_path}")

        except ValueError as ve: 
            QMessageBox.critical(self, "🚫 输入错误", f"页面范围解析错误: {ve}")
            self.status_label.setText(f"页面范围错误: {ve}")
            self.status_label.setStyleSheet("color: red;")
        except FileNotFoundError:
            QMessageBox.critical(self, "🚫 文件错误", f"输入 PDF 文件未找到: {input_pdf_path}")
            self.status_label.setText("错误：输入文件未找到")
            self.status_label.setStyleSheet("color: red;")
        except Exception as e:
            QMessageBox.critical(self, "🚫 处理错误", f"处理 PDF 时发生未知错误: {e}")
            self.status_label.setText(f"错误: {e}")
            self.status_label.setStyleSheet("color: red;")
        finally:
            QApplication.processEvents() 

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = PDFSplitterApp()
    main_window.show()
    sys.exit(app.exec())
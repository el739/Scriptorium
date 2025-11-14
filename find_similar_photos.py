#!/usr/bin/env python3
"""
图片相似度检测GUI工具
使用感知哈希算法查找文件夹中相似的图片，并提供可视化界面进行管理
"""

import os
import sys
from pathlib import Path
from PIL import Image
import imagehash
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QFileDialog, QSpinBox, QProgressBar, QScrollArea,
                             QGroupBox, QCheckBox, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap

# 支持的图片格式
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'}

class ImageScanThread(QThread):
    """图片扫描线程"""
    progress = pyqtSignal(int, int)  # 当前进度, 总数
    finished = pyqtSignal(dict)  # 完成信号，返回相似图片组
    status = pyqtSignal(str)  # 状态信息
    
    def __init__(self, directory, threshold):
        super().__init__()
        self.directory = directory
        self.threshold = threshold
        self.is_running = True
    
    def run(self):
        """执行扫描"""
        try:
            # 查找所有图片
            self.status.emit("正在扫描图片文件...")
            image_files = self.find_images(self.directory)
            
            if not image_files:
                self.status.emit("未找到任何图片文件")
                self.finished.emit({})
                return
            
            # 计算哈希值
            self.status.emit(f"找到 {len(image_files)} 张图片，正在计算哈希值...")
            image_hashes = {}
            
            for i, img_path in enumerate(image_files, 1):
                if not self.is_running:
                    return
                
                self.progress.emit(i, len(image_files))
                img_hash = self.calculate_hash(img_path)
                if img_hash is not None:
                    image_hashes[img_path] = img_hash
            
            # 查找相似图片
            self.status.emit("正在查找相似图片...")
            similar_groups = self.find_similar(image_hashes)
            
            self.status.emit(f"扫描完成！找到 {len(similar_groups)} 组相似图片")
            self.finished.emit(similar_groups)
            
        except Exception as e:
            self.status.emit(f"错误: {str(e)}")
            self.finished.emit({})
    
    def find_images(self, directory):
        """递归查找图片"""
        image_files = []
        directory = Path(directory)
        
        for file_path in directory.rglob('*'):
            if not self.is_running:
                break
            if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS:
                image_files.append(file_path)
        
        return image_files
    
    def calculate_hash(self, image_path):
        """计算图片哈希"""
        try:
            img = Image.open(image_path)
            return imagehash.average_hash(img, hash_size=8)
        except:
            return None
    
    def find_similar(self, image_hashes):
        """查找相似图片"""
        similar_groups = {}
        processed = set()
        image_list = list(image_hashes.items())
        
        for i, (path1, hash1) in enumerate(image_list):
            if path1 in processed or not self.is_running:
                continue
            
            group = [path1]
            
            for path2, hash2 in image_list[i+1:]:
                if path2 in processed:
                    continue
                
                difference = hash1 - hash2
                if difference <= self.threshold:
                    group.append(path2)
                    processed.add(path2)
            
            if len(group) > 1:
                similar_groups[i] = group
                processed.add(path1)
        
        return similar_groups
    
    def stop(self):
        """停止扫描"""
        self.is_running = False

class ImageWidget(QWidget):
    """单个图片显示组件"""
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # 图片预览
        self.image_label = QLabel()
        self.image_label.setFixedSize(200, 200)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")
        self.load_thumbnail()
        
        # 复选框
        self.checkbox = QCheckBox("删除此图片")
        self.checkbox.setStyleSheet("font-weight: bold; color: #d32f2f;")
        
        # 文件信息
        file_info = QLabel()
        file_name = os.path.basename(self.image_path)
        file_size = os.path.getsize(self.image_path) / 1024  # KB
        
        try:
            img = Image.open(self.image_path)
            dimensions = f"{img.width}x{img.height}"
        except:
            dimensions = "N/A"
        
        info_text = f"<b>{file_name}</b><br>大小: {file_size:.1f} KB<br>尺寸: {dimensions}"
        file_info.setText(info_text)
        file_info.setWordWrap(True)
        file_info.setAlignment(Qt.AlignCenter)
        
        # 路径标签（可点击查看完整路径）
        path_label = QLabel(f"<small>{str(self.image_path)[:50]}...</small>")
        path_label.setWordWrap(True)
        path_label.setAlignment(Qt.AlignCenter)
        path_label.setToolTip(str(self.image_path))
        
        layout.addWidget(self.image_label)
        layout.addWidget(self.checkbox)
        layout.addWidget(file_info)
        layout.addWidget(path_label)
        
        self.setLayout(layout)
        self.setMaximumWidth(220)
    
    def load_thumbnail(self):
        """加载缩略图"""
        try:
            pixmap = QPixmap(str(self.image_path))
            scaled_pixmap = pixmap.scaled(190, 190, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        except:
            self.image_label.setText("无法加载图片")
    
    def is_marked_for_deletion(self):
        """是否标记为删除"""
        return self.checkbox.isChecked()

class SimilarGroupWidget(QWidget):
    """相似图片组显示组件"""
    def __init__(self, group_id, image_paths, parent=None):
        super().__init__(parent)
        self.group_id = group_id
        self.image_paths = image_paths
        self.image_widgets = []
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QVBoxLayout()
        
        # 组标题
        group_box = QGroupBox(f"相似组 {self.group_id + 1} - 共 {len(self.image_paths)} 张图片")
        group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        group_layout = QVBoxLayout()
        
        # 批量操作按钮
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        deselect_all_btn = QPushButton("取消全选")
        keep_first_btn = QPushButton("仅保留第一张")
        keep_largest_btn = QPushButton("仅保留最大文件")
        
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn.clicked.connect(self.deselect_all)
        keep_first_btn.clicked.connect(self.keep_first_only)
        keep_largest_btn.clicked.connect(self.keep_largest_only)
        
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        button_layout.addWidget(keep_first_btn)
        button_layout.addWidget(keep_largest_btn)
        button_layout.addStretch()
        
        group_layout.addLayout(button_layout)
        
        # 图片显示区域
        images_layout = QHBoxLayout()
        images_layout.setSpacing(10)
        
        for img_path in self.image_paths:
            img_widget = ImageWidget(img_path)
            self.image_widgets.append(img_widget)
            images_layout.addWidget(img_widget)
        
        images_layout.addStretch()
        
        group_layout.addLayout(images_layout)
        group_box.setLayout(group_layout)
        
        main_layout.addWidget(group_box)
        self.setLayout(main_layout)
    
    def select_all(self):
        """全选"""
        for widget in self.image_widgets:
            widget.checkbox.setChecked(True)
    
    def deselect_all(self):
        """取消全选"""
        for widget in self.image_widgets:
            widget.checkbox.setChecked(False)
    
    def keep_first_only(self):
        """仅保留第一张"""
        for i, widget in enumerate(self.image_widgets):
            widget.checkbox.setChecked(i != 0)
    
    def keep_largest_only(self):
        """仅保留最大文件"""
        largest_idx = 0
        largest_size = 0
        
        for i, widget in enumerate(self.image_widgets):
            size = os.path.getsize(widget.image_path)
            if size > largest_size:
                largest_size = size
                largest_idx = i
        
        for i, widget in enumerate(self.image_widgets):
            widget.checkbox.setChecked(i != largest_idx)
    
    def get_marked_for_deletion(self):
        """获取标记为删除的图片路径"""
        return [w.image_path for w in self.image_widgets if w.is_marked_for_deletion()]

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.similar_groups = {}
        self.group_widgets = []
        self.scan_thread = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("图片相似度检测工具")
        self.setGeometry(100, 100, 1200, 800)
        
        # 主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout()
        
        # 顶部控制面板
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("请选择文件夹开始扫描")
        self.status_label.setStyleSheet("padding: 5px; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # 结果显示区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout()
        self.results_widget.setLayout(self.results_layout)
        self.scroll_area.setWidget(self.results_widget)
        
        layout.addWidget(self.scroll_area)
        
        # 底部操作按钮
        bottom_buttons = QHBoxLayout()
        
        self.delete_btn = QPushButton("删除选中的图片")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.setEnabled(False)
        
        bottom_buttons.addStretch()
        bottom_buttons.addWidget(self.delete_btn)
        
        layout.addLayout(bottom_buttons)
        
        main_widget.setLayout(layout)
    
    def create_control_panel(self):
        """创建控制面板"""
        panel = QGroupBox("扫描设置")
        layout = QHBoxLayout()
        
        # 文件夹选择
        layout.addWidget(QLabel("文件夹:"))
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("选择要扫描的文件夹...")
        layout.addWidget(self.folder_input)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_folder)
        layout.addWidget(browse_btn)
        
        # 阈值设置
        layout.addWidget(QLabel("相似度阈值:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 20)
        self.threshold_spin.setValue(5)
        self.threshold_spin.setToolTip("值越小表示越相似 (0=完全相同, 1-5=非常相似)")
        layout.addWidget(self.threshold_spin)
        
        # 开始扫描按钮
        self.scan_btn = QPushButton("开始扫描")
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.scan_btn.clicked.connect(self.start_scan)
        layout.addWidget(self.scan_btn)
        
        panel.setLayout(layout)
        return panel
    
    def browse_folder(self):
        """浏览文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self.folder_input.setText(folder)
    
    def start_scan(self):
        """开始扫描"""
        directory = self.folder_input.text()
        
        if not directory:
            QMessageBox.warning(self, "警告", "请先选择文件夹！")
            return
        
        if not os.path.exists(directory):
            QMessageBox.warning(self, "警告", "文件夹不存在！")
            return
        
        # 清空之前的结果
        self.clear_results()
        
        # 禁用控件
        self.scan_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 启动扫描线程
        threshold = self.threshold_spin.value()
        self.scan_thread = ImageScanThread(directory, threshold)
        self.scan_thread.progress.connect(self.update_progress)
        self.scan_thread.status.connect(self.update_status)
        self.scan_thread.finished.connect(self.scan_finished)
        self.scan_thread.start()
    
    def update_progress(self, current, total):
        """更新进度"""
        self.progress_bar.setValue(int(current / total * 100))
    
    def update_status(self, message):
        """更新状态"""
        self.status_label.setText(message)
    
    def scan_finished(self, similar_groups):
        """扫描完成"""
        self.similar_groups = similar_groups
        self.scan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if not similar_groups:
            self.status_label.setText("未找到相似的图片")
            return
        
        # 显示结果
        for group_id, image_paths in similar_groups.items():
            group_widget = SimilarGroupWidget(group_id, image_paths)
            self.group_widgets.append(group_widget)
            self.results_layout.addWidget(group_widget)
        
        self.results_layout.addStretch()
        self.delete_btn.setEnabled(True)
    
    def clear_results(self):
        """清空结果"""
        for widget in self.group_widgets:
            self.results_layout.removeWidget(widget)
            widget.deleteLater()
        
        self.group_widgets.clear()
        self.similar_groups.clear()
    
    def delete_selected(self):
        """删除选中的图片"""
        # 收集所有标记为删除的图片
        to_delete = []
        for group_widget in self.group_widgets:
            to_delete.extend(group_widget.get_marked_for_deletion())
        
        if not to_delete:
            QMessageBox.information(self, "提示", "没有选中任何图片！")
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除 {len(to_delete)} 张图片吗？\n此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success_count = 0
            fail_count = 0
            
            for img_path in to_delete:
                try:
                    os.remove(img_path)
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    print(f"删除失败 {img_path}: {e}")
            
            QMessageBox.information(
                self, 
                "删除完成", 
                f"成功删除 {success_count} 张图片\n失败 {fail_count} 张"
            )
            
            # 清空结果，让用户重新扫描
            self.clear_results()
            self.status_label.setText("删除完成，请重新扫描以查看最新结果")

def main():
    """主函数"""
    # 检查依赖
    try:
        import imagehash
    except ImportError:
        print("错误: 需要安装 imagehash 库")
        print("请运行: pip install imagehash pillow PyQt5")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
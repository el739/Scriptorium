#!/usr/bin/env python3
"""
游戏存档管理器 - 监视指定文件变化并管理历史副本
依赖: pip install PyQt5 watchdog
"""

import sys
import os
import shutil
import json
import time
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QScrollArea,
    QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QBrush

MAX_SAVES = 10
SAVES_DIR = Path.home() / ".game_sl_saves"
META_FILE = SAVES_DIR / "meta.json"


# ─── 文件监视器 ───────────────────────────────────────────────
class FileWatcher(QThread):
    file_changed = pyqtSignal(str)

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        self._running = True
        self._last_mtime = None

    def run(self):
        if not os.path.exists(self.filepath):
            return
        self._last_mtime = os.path.getmtime(self.filepath)
        while self._running:
            try:
                mtime = os.path.getmtime(self.filepath)
                if mtime != self._last_mtime:
                    self._last_mtime = mtime
                    self.file_changed.emit(self.filepath)
            except Exception:
                pass
            time.sleep(0.5)

    def stop(self):
        self._running = False


# ─── 存档管理 ─────────────────────────────────────────────────
class SaveManager:
    """
    meta.json 结构（新版）：
    {
      "last_watched": "/path/to/file",
      "files": {
        "/path/to/fileA": { "saves": [...] },
        "/path/to/fileB": { "saves": [...] }
      }
    }
    每个文件拥有独立的存档列表，切换文件不会互相污染。
    """

    def __init__(self):
        SAVES_DIR.mkdir(exist_ok=True)
        self.meta = self._load_meta()
        self._current_file = self.meta.get("last_watched", "")

    # ── 持久化 ──────────────────────────────────────────────
    def _load_meta(self):
        if META_FILE.exists():
            try:
                with open(META_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 兼容旧版格式（全局 saves 列表）→ 自动迁移到新格式
                if "saves" in data and "files" not in data:
                    watched = data.get("watched_file", "")
                    new_data = {"last_watched": watched, "files": {}}
                    if watched and data["saves"]:
                        new_data["files"][watched] = {"saves": data["saves"]}
                    return new_data
                return data
            except Exception:
                pass
        return {"last_watched": "", "files": {}}

    def _save_meta(self):
        with open(META_FILE, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, ensure_ascii=False, indent=2)

    # ── 当前文件 ─────────────────────────────────────────────
    @property
    def current_file(self):
        return self._current_file

    def switch_file(self, path):
        """切换监视的文件，各文件存档完全隔离。"""
        self._current_file = path
        self.meta["last_watched"] = path
        self.meta.setdefault("files", {}).setdefault(path, {"saves": []})
        self._save_meta()

    # ── 当前文件的存档列表 ────────────────────────────────────
    @property
    def saves(self):
        if not self._current_file:
            return []
        return self.meta.get("files", {}).get(self._current_file, {}).get("saves", [])

    def _set_saves(self, saves_list):
        self.meta.setdefault("files", {}).setdefault(self._current_file, {})["saves"] = saves_list
        self._save_meta()

    # ── 存档操作 ──────────────────────────────────────────────
    def create_save(self, source_path, label=""):
        ts = datetime.now()
        ts_str = ts.strftime("%Y%m%d_%H%M%S")
        ext = Path(source_path).suffix
        # 以文件路径哈希为前缀，避免不同文件的存档文件名冲突
        file_hash = str(abs(hash(source_path)))[:6]
        save_name = f"{file_hash}_{ts_str}{ext}"
        save_path = SAVES_DIR / save_name
        shutil.copy2(source_path, save_path)

        entry = {
            "id": f"{file_hash}_{ts_str}",
            "timestamp": ts.isoformat(),
            "display_time": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "label": label or ts.strftime("存档 %H:%M:%S"),
            "filename": save_name,
            "size": os.path.getsize(source_path),
        }
        saves = list(self.saves)
        saves.insert(0, entry)

        # 超出上限时删除最旧的存档文件
        removed = saves[MAX_SAVES:]
        saves = saves[:MAX_SAVES]
        for r in removed:
            p = SAVES_DIR / r["filename"]
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass

        self._set_saves(saves)
        return entry

    def restore_save(self, save_id, target_path):
        for s in self.saves:
            if s["id"] == save_id:
                save_path = SAVES_DIR / s["filename"]
                if save_path.exists():
                    shutil.copy2(save_path, target_path)
                    return True
        return False

    def delete_save(self, save_id):
        saves = list(self.saves)
        for i, s in enumerate(saves):
            if s["id"] == save_id:
                p = SAVES_DIR / s["filename"]
                if p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass
                saves.pop(i)
                self._set_saves(saves)
                return True
        return False


# ─── 存档卡片组件 ─────────────────────────────────────────────
class SaveCard(QFrame):
    restore_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, entry, is_latest=False):
        super().__init__()
        self.entry = entry
        self.save_id = entry["id"]
        self._build_ui(is_latest)

    def _build_ui(self, is_latest):
        self.setFixedHeight(98)
        self.setObjectName("saveCard")

        if is_latest:
            self.setStyleSheet("""
                #saveCard {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #1a3a2a, stop:1 #0d2010);
                    border: 1px solid #4ade80;
                    border-left: 4px solid #4ade80;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                #saveCard {
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #1a1f2e, stop:1 #111520);
                    border: 1px solid #2a3040;
                    border-left: 4px solid #3b5bdb;
                    border-radius: 8px;
                }
                #saveCard:hover {
                    border-color: #4c6ef5;
                    border-left-color: #748ffc;
                }
            """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 12, 12)
        layout.setSpacing(14)

        # 时间圆点
        dot_color = "#4ade80" if is_latest else "#3b5bdb"
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {dot_color}; font-size: 16px; background: transparent;")
        dot.setFixedWidth(22)
        layout.addWidget(dot)

        # 信息区
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)

        label_text = self.entry.get("label", "")
        if is_latest:
            label_text = "🟢 " + label_text + "  [最新]"
        name_label = QLabel(label_text)
        name_label.setStyleSheet(
            "color: #e2e8f0; font-size: 14px; font-weight: bold; background: transparent;"
        )

        time_label = QLabel(self.entry.get("display_time", ""))
        time_label.setStyleSheet("color: #64748b; font-size: 13px; background: transparent;")

        size_kb = self.entry.get("size", 0) / 1024
        size_label = QLabel(f"{size_kb:.1f} KB")
        size_label.setStyleSheet("color: #475569; font-size: 11px; background: transparent;")

        info_layout.addWidget(name_label)
        info_layout.addWidget(time_label)
        info_layout.addWidget(size_label)
        layout.addLayout(info_layout)
        layout.addStretch()

        # 按钮区
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(5)

        restore_btn = QPushButton("恢复")
        restore_btn.setFixedSize(66, 32)
        restore_btn.setStyleSheet("""
            QPushButton {
                background: #1d4ed8;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2563eb; }
            QPushButton:pressed { background: #1e40af; }
        """)
        restore_btn.clicked.connect(lambda: self.restore_requested.emit(self.save_id))

        del_btn = QPushButton("删除")
        del_btn.setFixedSize(66, 26)
        del_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748b;
                border: 1px solid #334155;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { color: #ef4444; border-color: #ef4444; }
        """)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.save_id))

        btn_layout.addWidget(restore_btn)
        btn_layout.addWidget(del_btn)
        layout.addLayout(btn_layout)


# ─── 主窗口 ───────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.save_manager = SaveManager()
        self.watcher = None
        self.setWindowTitle("游戏存档管理器 · SL System")
        self.setMinimumSize(580, 720)
        self.resize(620, 780)
        self._apply_global_style()
        self._build_ui()

        # 恢复上次监视的文件
        last = self.save_manager.current_file
        if last and os.path.exists(last):
            self._start_watching(last)
            self._update_path_display(last)

        self._refresh_timeline()

        self._status_timer = QTimer()
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(lambda: self.status_label.setText(""))

    def _apply_global_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget#central {
                background-color: #0a0e1a;
            }
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: #111827; width: 7px; border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #2d3748; border-radius: 3px; min-height: 24px;
            }
            QScrollBar::handle:vertical:hover { background: #4a5568; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(26, 26, 26, 26)
        root.setSpacing(0)

        # ── 标题栏 ──
        title_row = QHBoxLayout()
        icon_label = QLabel("⚔")
        icon_label.setStyleSheet("color: #4ade80; font-size: 30px;")
        title_label = QLabel("游戏存档管理器")
        title_label.setStyleSheet("""
            color: #f1f5f9;
            font-size: 22px;
            font-weight: bold;
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            letter-spacing: 1px;
        """)
        sub = QLabel("SL System — Save & Load")
        sub.setStyleSheet("color: #475569; font-size: 12px; margin-left: 4px;")
        title_row.addWidget(icon_label)
        title_row.addSpacing(10)
        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_col.addWidget(title_label)
        title_col.addWidget(sub)
        title_row.addLayout(title_col)
        title_row.addStretch()
        root.addLayout(title_row)
        root.addSpacing(22)

        # ── 文件选择区 ──
        file_frame = QFrame()
        file_frame.setStyleSheet("""
            QFrame {
                background: #111827;
                border: 1px solid #1f2937;
                border-radius: 10px;
            }
        """)
        file_layout = QVBoxLayout(file_frame)
        file_layout.setContentsMargins(18, 15, 18, 15)
        file_layout.setSpacing(10)

        fl_title = QLabel("监视文件")
        fl_title.setStyleSheet(
            "color: #94a3b8; font-size: 12px; font-weight: bold; "
            "letter-spacing: 1px; background: transparent;"
        )
        file_layout.addWidget(fl_title)

        path_row = QHBoxLayout()
        self.file_path_label = QLabel("未选择文件")
        self.file_path_label.setStyleSheet("""
            color: #64748b;
            font-size: 13px;
            background: #0d1117;
            border: 1px solid #1f2937;
            border-radius: 6px;
            padding: 6px 10px;
        """)
        self.file_path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.file_path_label.setFixedHeight(36)

        choose_btn = QPushButton("选择文件")
        choose_btn.setFixedSize(96, 36)
        choose_btn.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background: #263548; color: #e2e8f0; }
        """)
        choose_btn.clicked.connect(self._choose_file)

        path_row.addWidget(self.file_path_label)
        path_row.addSpacing(8)
        path_row.addWidget(choose_btn)
        file_layout.addLayout(path_row)

        # 监视状态 + 手动存档
        status_row = QHBoxLayout()
        self.watch_dot = QLabel("●")
        self.watch_dot.setStyleSheet("color: #374151; font-size: 11px; background: transparent;")
        self.watch_status = QLabel("未监视")
        self.watch_status.setStyleSheet("color: #4b5563; font-size: 13px; background: transparent;")

        self.manual_save_btn = QPushButton("手动存档")
        self.manual_save_btn.setFixedSize(88, 30)
        self.manual_save_btn.setStyleSheet("""
            QPushButton {
                background: #064e3b;
                color: #6ee7b7;
                border: 1px solid #065f46;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background: #065f46; }
            QPushButton:disabled { background: #1f2937; color: #374151; border-color: #1f2937; }
        """)
        self.manual_save_btn.clicked.connect(self._manual_save)
        self.manual_save_btn.setEnabled(False)

        status_row.addWidget(self.watch_dot)
        status_row.addSpacing(5)
        status_row.addWidget(self.watch_status)
        status_row.addStretch()
        status_row.addWidget(self.manual_save_btn)
        file_layout.addLayout(status_row)

        root.addWidget(file_frame)
        root.addSpacing(22)

        # ── 时间线标题 ──
        tl_header = QHBoxLayout()
        tl_title = QLabel("存档时间线")
        tl_title.setStyleSheet(
            "color: #94a3b8; font-size: 12px; font-weight: bold; letter-spacing: 1px;"
        )
        self.save_count_label = QLabel("0 / 10")
        self.save_count_label.setStyleSheet("color: #475569; font-size: 13px;")
        tl_header.addWidget(tl_title)
        tl_header.addStretch()
        tl_header.addWidget(self.save_count_label)
        root.addLayout(tl_header)
        root.addSpacing(10)

        # 进度条
        self.progress_bar = TimelineProgressBar()
        self.progress_bar.setFixedHeight(7)
        root.addWidget(self.progress_bar)
        root.addSpacing(14)

        # 存档卡片列表
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.setSpacing(9)
        self.cards_layout.addStretch()
        self.scroll.setWidget(self.cards_container)
        root.addWidget(self.scroll, 1)
        root.addSpacing(12)

        # 底部状态
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #4ade80; font-size: 13px; min-height: 20px;")
        root.addWidget(self.status_label)

    # ── 辅助 ─────────────────────────────────────────────────
    def _show_status(self, msg, color="#4ade80", duration=3000):
        self.status_label.setStyleSheet(f"color: {color}; font-size: 13px; min-height: 20px;")
        self.status_label.setText(msg)
        self._status_timer.start(duration)

    def _update_path_display(self, path):
        self.file_path_label.setText(path)
        self.file_path_label.setStyleSheet("""
            color: #e2e8f0;
            font-size: 13px;
            background: #0d1117;
            border: 1px solid #1f2937;
            border-radius: 6px;
            padding: 6px 10px;
        """)

    def _set_watching_ui(self, active: bool):
        if active:
            self.watch_dot.setStyleSheet("color: #4ade80; font-size: 11px; background: transparent;")
            self.watch_status.setStyleSheet("color: #4ade80; font-size: 13px; background: transparent;")
            self.watch_status.setText("监视中")
            self.manual_save_btn.setEnabled(True)
        else:
            self.watch_dot.setStyleSheet("color: #374151; font-size: 11px; background: transparent;")
            self.watch_status.setStyleSheet("color: #4b5563; font-size: 13px; background: transparent;")
            self.watch_status.setText("未监视")
            self.manual_save_btn.setEnabled(False)

    # ── 文件选择与监视 ────────────────────────────────────────
    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择要监视的文件", "", "所有文件 (*)")
        if not path:
            return

        # 选了同一个文件，无需重复操作
        if path == self.save_manager.current_file:
            self._show_status("已在监视此文件", "#f59e0b")
            return

        # 切换文件：存档列表彼此完全隔离
        self.save_manager.switch_file(path)
        self._start_watching(path)
        self._update_path_display(path)
        self._refresh_timeline()   # 立即显示新文件的（可能为空的）存档列表
        self._show_status(f"✓ 已切换文件，存档独立管理，当前共 {len(self.save_manager.saves)} 条存档")

    def _start_watching(self, path):
        if self.watcher:
            self.watcher.stop()
            self.watcher.wait()
        self.watcher = FileWatcher(path)
        self.watcher.file_changed.connect(self._on_file_changed)
        self.watcher.start()
        self._set_watching_ui(True)

    # ── 存档操作 ──────────────────────────────────────────────
    def _on_file_changed(self, path):
        entry = self.save_manager.create_save(path)
        self._refresh_timeline()
        self._show_status(f"✓ 检测到变化，已自动存档 [{entry['display_time']}]")

    def _manual_save(self):
        path = self.save_manager.current_file
        if not path or not os.path.exists(path):
            self._show_status("错误：文件不存在", "#ef4444")
            return
        entry = self.save_manager.create_save(
            path, label="手动存档 " + datetime.now().strftime("%H:%M:%S")
        )
        self._refresh_timeline()
        self._show_status(f"✓ 手动存档成功 [{entry['display_time']}]")

    def _refresh_timeline(self):
        # 清空旧卡片（保留末尾 stretch）
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        saves = self.save_manager.saves
        self.save_count_label.setText(f"{len(saves)} / {MAX_SAVES}")
        self.progress_bar.set_progress(len(saves), MAX_SAVES)

        if saves:
            for i, entry in enumerate(saves):
                card = SaveCard(entry, is_latest=(i == 0))
                card.restore_requested.connect(self._restore_save)
                card.delete_requested.connect(self._delete_save)
                self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        else:
            placeholder = QLabel("暂无存档\n选择文件后，文件变化将自动创建存档")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet(
                "color: #374151; font-size: 14px; padding: 48px; background: transparent;"
            )
            self.cards_layout.insertWidget(0, placeholder)

    def _restore_save(self, save_id):
        path = self.save_manager.current_file
        if not path:
            self._show_status("错误：未指定目标文件", "#ef4444")
            return
        reply = QMessageBox.question(
            self, "确认恢复",
            "确定要将文件恢复到此存档吗？\n当前文件内容将被覆盖。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.save_manager.restore_save(save_id, path):
                self._show_status("✓ 恢复成功！文件已还原到指定存档")
            else:
                self._show_status("错误：存档文件不存在", "#ef4444")

    def _delete_save(self, save_id):
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除此存档吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.save_manager.delete_save(save_id)
            self._refresh_timeline()
            self._show_status("存档已删除", "#f59e0b")

    def closeEvent(self, event):
        if self.watcher:
            self.watcher.stop()
            self.watcher.wait()
        event.accept()


# ─── 时间线进度条 ─────────────────────────────────────────────
class TimelineProgressBar(QWidget):
    def __init__(self):
        super().__init__()
        self._value = 0
        self._max = MAX_SAVES

    def set_progress(self, value, max_val):
        self._value = value
        self._max = max_val
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#1f2937")))
        p.drawRoundedRect(0, 0, w, h, r, r)

        if self._max > 0 and self._value > 0:
            prog_w = int(w * self._value / self._max)
            grad = QLinearGradient(0, 0, prog_w, 0)
            grad.setColorAt(0, QColor("#3b5bdb"))
            grad.setColorAt(1, QColor("#4ade80"))
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(0, 0, prog_w, h, r, r)

        p.end()


# ─── 入口 ─────────────────────────────────────────────────────
def main():
    try:
        import watchdog  # noqa
    except ImportError:
        print("缺少依赖，请运行: pip install PyQt5 watchdog")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("游戏存档管理器")

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
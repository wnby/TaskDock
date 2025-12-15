import sys
import json
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QListWidget, 
                             QListWidgetItem, QLineEdit, QLabel, QProgressBar,
                             QHBoxLayout, QFrame, QSystemTrayIcon, QMenu, QAction, 
                             QStyle, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QTimer, QEasingCurve
from PyQt5.QtGui import QColor, QFont, QIcon

class TaskManager:
    def __init__(self, filename="tasks.json"):
        self.filename = filename
        self.load()

    def load(self):
        if not os.path.exists(self.filename):
            self.data = {"last_date": "", "daily": [], "todo": []}
        else:
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except:
                self.data = {"last_date": "", "daily": [], "todo": []}
        
        today = datetime.now().strftime("%Y-%m-%d")
        if self.data.get("last_date") != today:
            for task in self.data.get("daily", []):
                task["done"] = False
            self.data["last_date"] = today
            self.save()

    def save(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_task(self, text, is_daily=False):
        target = self.data["daily"] if is_daily else self.data["todo"]
        target.append({"text": text, "done": False})
        self.save()

    def toggle_task(self, is_daily, index):
        target = self.data["daily"] if is_daily else self.data["todo"]
        if 0 <= index < len(target):
            target[index]["done"] = not target[index]["done"]
            self.save()
    
    def remove_task(self, is_daily, index):
        target = self.data["daily"] if is_daily else self.data["todo"]
        if 0 <= index < len(target):
            del target[index]
            self.save()

    def get_undone_count(self):
        """获取未完成任务数量"""
        count = 0
        for t in self.data["daily"]:
            if not t["done"]: count += 1
        for t in self.data["todo"]:
            if not t["done"]: count += 1
        return count

# === 界面 ===
class FancyItemWidget(QWidget):
    def __init__(self, text, is_done, is_daily):
        super().__init__()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        status_char = "✨" if is_done else "🔹"
        self.lbl_status = QLabel(status_char)
        self.lbl_status.setFont(QFont("Segoe UI Emoji", 10))
        
        self.lbl_text = QLabel(text)
        font = QFont("Microsoft YaHei", 10)
        if is_done:
            font.setStrikeOut(True)
            self.lbl_text.setStyleSheet("color: rgba(255,255,255,0.4);")
        else:
            self.lbl_text.setStyleSheet("color: white; font-weight: bold;")
        self.lbl_text.setFont(font)
        
        type_str = " DAILY " if is_daily else " TODO "
        type_bg = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF512F, stop:1 #DD2476)" if is_daily else "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00d2ff, stop:1 #3a7bd5)"
        
        self.lbl_type = QLabel(type_str)
        self.lbl_type.setStyleSheet(f"background: {type_bg}; color: white; border-radius: 8px; font-size: 9px; font-weight: bold; padding: 2px;")
        self.lbl_type.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.lbl_text)
        layout.addStretch()
        layout.addWidget(self.lbl_type)
        self.setLayout(layout)

# === 主窗口 ===
class FancyDock(QWidget):
    def __init__(self):
        super().__init__()
        self.tm = TaskManager()
        
        # 配置
        self.win_width = 320
        self.peek_width = 45 
        self.win_height = 450
        self.top_margin = 120 # 距离顶部距离
        
        self.is_expanded = False
        
        self.init_ui()
        self.init_tray()
        self.refresh_list()
        self.reset_position()

        # 每隔 45 分钟检查一次 (45 * 60 * 1000 毫秒)
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start(45 * 60 * 1000) 

    def check_reminders(self):
        """检查未完成任务并发送通知"""
        count = self.tm.get_undone_count()
        if count > 0:
            # 发送 Windows 通知气泡
            self.tray.showMessage(
                "任务提醒", 
                f"还有 {count} 个任务没做完呢！加油！(OwO)", 
                QSystemTrayIcon.Information, 
                5000 # 显示5秒
            )
            # 让把手变成红色
            self.neon_strip.setStyleSheet("background-color: #FF0000; border-radius: 3px;")

    def reset_position(self):
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.peek_width
        y = screen.top() + self.top_margin
        self.setGeometry(x, y, self.win_width, self.win_height)
        self.is_expanded = False

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(main_layout)
        
        # 容器
        self.container = QFrame()
        self.container.setObjectName("Container")
        self.container.setStyleSheet("""
            QFrame#Container {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #141E30, stop:1 #243B55);
                border-top-left-radius: 20px;
                border-bottom-left-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(-2, 2)
        self.container.setGraphicsEffect(shadow)
        main_layout.addWidget(self.container)
        
        container_layout = QHBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        self.container.setLayout(container_layout)
        
        # 左侧把手
        self.handle_frame = QFrame()
        self.handle_frame.setFixedWidth(30)
        self.handle_frame.setStyleSheet("background: transparent; border-right: 1px solid rgba(255,255,255,20);")
        handle_layout = QVBoxLayout()
        self.handle_frame.setLayout(handle_layout)
        
        self.neon_strip = QLabel()
        self.neon_strip.setFixedSize(6, 40)
        self.neon_strip.setStyleSheet("background-color: #00f260; border-radius: 3px;")
        
        self.arrow = QLabel("◀")
        self.arrow.setStyleSheet("color: rgba(255,255,255,150); font-weight: bold;")
        
        handle_layout.addStretch()
        handle_layout.addWidget(self.neon_strip, 0, Qt.AlignCenter)
        handle_layout.addSpacing(10)
        handle_layout.addWidget(self.arrow, 0, Qt.AlignCenter)
        handle_layout.addStretch()
        container_layout.addWidget(self.handle_frame)
        
        # 右侧内容
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(5, 10, 10, 10)
        self.content_frame.setLayout(content_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: rgba(0,0,0,50); border-radius: 2px; } QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f260, stop:1 #0575E6); border-radius: 2px; }")
        content_layout.addWidget(self.progress_bar)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("border: none; background: transparent; outline: none;")
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        content_layout.addWidget(self.list_widget)
        
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText(" Type here... (加*为日常)")
        self.input_box.setStyleSheet("QLineEdit { background: rgba(255, 255, 255, 20); color: white; border: 1px solid rgba(255, 255, 255, 30); border-radius: 15px; padding: 8px 15px; font-family: 'Microsoft YaHei'; } QLineEdit:focus { background: rgba(255, 255, 255, 40); border: 1px solid rgba(255, 255, 255, 80); }")
        self.input_box.returnPressed.connect(self.handle_input)
        content_layout.addWidget(self.input_box)
        
        container_layout.addWidget(self.content_frame)

    # --- 交互 ---
    def enterEvent(self, event):
        self.animate(True)
        
    def leaveEvent(self, event):
        if not self.input_box.hasFocus():
            self.animate(False)

    def animate(self, expand):
        if self.is_expanded == expand: return
        self.is_expanded = expand
        
        screen_width = QApplication.primaryScreen().geometry().width()
        current_y = self.geometry().y()
        target_x = screen_width - self.win_width if expand else screen_width - self.peek_width
        
        self.arrow.setText("▶" if expand else "◀")
        # 恢复绿色，或者如果是红色警示态，展开时也许可以变回绿色
        self.neon_strip.setStyleSheet(f"background-color: {'#ec008c' if expand else '#00f260'}; border-radius: 3px;")
        
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.OutBack)
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(QRect(target_x, current_y, self.win_width, self.win_height))
        self.anim.start()

    # --- 托盘 ---
    def init_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        menu = QMenu()
        menu.addAction("🔄 复位位置", self.reset_position)
        menu.addAction("❌ 退出", QApplication.instance().quit)
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.tray.showMessage("已启动", "我在右上角等你哦", QSystemTrayIcon.Information, 2000)

    # --- 业务逻辑 ---
    def refresh_list(self):
        self.list_widget.clear()
        total = 0; done_c = 0
        for t in self.tm.data["daily"]:
            self.add_item(t["text"], t["done"], True)
            total+=1; done_c += 1 if t["done"] else 0
        for t in self.tm.data["todo"]:
            self.add_item(t["text"], t["done"], False)
            total+=1; done_c += 1 if t["done"] else 0
        val = 0 if total == 0 else int((done_c/total)*100)
        self.progress_bar.setValue(val)
        
        # 如果全做完了，把霓虹灯变绿
        if done_c == total and total > 0:
            self.neon_strip.setStyleSheet("background-color: #00f260; border-radius: 3px;")

    def add_item(self, text, done, is_daily):
        item = QListWidgetItem()
        widget = FancyItemWidget(text, done, is_daily)
        item.setSizeHint(widget.sizeHint())
        item.setData(Qt.UserRole, {"daily": is_daily, "text": text})
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)

    def on_item_clicked(self, item):
        data = item.data(Qt.UserRole)
        target = self.tm.data["daily"] if data["daily"] else self.tm.data["todo"]
        for i, task in enumerate(target):
            if task["text"] == data["text"]:
                self.tm.toggle_task(data["daily"], i)
                break
        self.refresh_list()

    def handle_input(self):
        text = self.input_box.text().strip()
        if not text: return
        is_daily = "*" in text
        clean_text = text.replace("*", "").strip()
        self.tm.add_task(clean_text, is_daily)
        self.input_box.clear()
        self.refresh_list()

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return
        menu = QMenu()
        del_act = menu.addAction("🗑️ 删除此任务")
        if menu.exec_(self.list_widget.mapToGlobal(pos)) == del_act:
            data = item.data(Qt.UserRole)
            target = self.tm.data["daily"] if data["daily"] else self.tm.data["todo"]
            for i, task in enumerate(target):
                if task["text"] == data["text"]:
                    self.tm.remove_task(data["daily"], i)
                    break
            self.refresh_list()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) 
    dock = FancyDock()
    dock.show()
    sys.exit(app.exec_())

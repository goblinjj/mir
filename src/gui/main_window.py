"""Main GUI window for MirBot."""

import sys
import threading

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QTextEdit, QGroupBox,
    QLineEdit, QApplication,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont

from src.bot import MirBot
from src.gui.minimap_widget import MinimapWidget
from src.utils.logger import log


class BotWindow(QMainWindow):
    """Main control window for MirBot."""

    log_signal = pyqtSignal(str)

    def __init__(self, config_path: str = "config.yaml"):
        super().__init__()
        self.config_path = config_path
        self.bot = None
        self.bot_thread = None
        self._init_ui()
        self.log_signal.connect(self._append_log)

    def _init_ui(self):
        self.setWindowTitle("MirBot - 热血传奇法师练级")
        self.setMinimumSize(500, 400)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Status
        status_group = QGroupBox("状态")
        status_layout = QHBoxLayout(status_group)
        self.status_label = QLabel("已停止")
        self.status_label.setFont(QFont("", 14, QFont.Bold))
        self.hp_label = QLabel("HP: --%")
        self.mp_label = QLabel("MP: --%")
        self.state_label = QLabel("状态: --")
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.hp_label)
        status_layout.addWidget(self.mp_label)
        status_layout.addWidget(self.state_label)
        layout.addWidget(status_group)

        # Controls
        ctrl_group = QGroupBox("控制")
        ctrl_layout = QHBoxLayout(ctrl_group)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["fire - 火力输出", "pet - 宝宝练级"])
        ctrl_layout.addWidget(QLabel("模式:"))
        ctrl_layout.addWidget(self.mode_combo)

        self.start_btn = QPushButton("启动")
        self.start_btn.clicked.connect(self._on_start)
        ctrl_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        ctrl_layout.addWidget(self.stop_btn)

        layout.addWidget(ctrl_group)

        # Monster whitelist
        monster_group = QGroupBox("怪物白名单")
        monster_layout = QHBoxLayout(monster_group)
        monster_layout.addWidget(QLabel("怪物名称:"))
        self.monster_input = QLineEdit()
        self.monster_input.setPlaceholderText("用逗号分隔，如: 鸡,鹿,稻草人,半兽人")
        monster_layout.addWidget(self.monster_input)
        layout.addWidget(monster_group)

        # --- Minimap / Waypoint group ---
        minimap_group = QGroupBox("巡逻路径 (左键添加 / 右键删除)")
        minimap_layout = QVBoxLayout()

        self.minimap_widget = MinimapWidget()
        minimap_layout.addWidget(self.minimap_widget)

        btn_layout = QHBoxLayout()
        self.btn_refresh_map = QPushButton("刷新地图")
        self.btn_clear_waypoints = QPushButton("清空路径")
        btn_layout.addWidget(self.btn_refresh_map)
        btn_layout.addWidget(self.btn_clear_waypoints)
        minimap_layout.addLayout(btn_layout)

        minimap_group.setLayout(minimap_layout)
        layout.addWidget(minimap_group)

        self.btn_refresh_map.clicked.connect(self._refresh_minimap)
        self.btn_clear_waypoints.clicked.connect(self.minimap_widget.clear_waypoints)
        self.minimap_widget.waypoints_changed.connect(self._on_waypoints_changed)

        # Log
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)

        # Status update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_status)
        self.timer.start(500)

    def _on_start(self):
        mode = self.mode_combo.currentText().split(" - ")[0]
        try:
            self.bot = MirBot(self.config_path)
            # Parse monster whitelist from GUI input
            raw = self.monster_input.text().strip()
            if raw:
                names = [n.strip() for n in raw.replace("，", ",").split(",") if n.strip()]
                self.bot.config.leveling.monster_names = names
                self.bot.monster_detector.monster_names = names
                self._append_log(f"怪物白名单: {names}")
            self.bot.set_mode(mode)
            if self.bot.config.patrol.waypoints:
                self.minimap_widget.set_waypoints(self.bot.config.patrol.waypoints)
        except Exception as e:
            self._append_log(f"初始化失败: {e}")
            return

        self.bot_thread = threading.Thread(target=self.bot.start, daemon=True)
        self.bot_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("运行中")
        self._append_log(f"Bot 已启动，模式: {mode}")

    def _on_stop(self):
        self._save_waypoints()
        if self.bot:
            self.bot.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("已停止")
        self._append_log("Bot 已停止")

    def _update_status(self):
        if self.bot and self.bot.running:
            gs = self.bot.game_state
            self.hp_label.setText(f"HP: {gs.player.hp_ratio:.0%}")
            self.mp_label.setText(f"MP: {gs.player.mp_ratio:.0%}")
            if self.bot.strategy.current_state:
                self.state_label.setText(f"状态: {self.bot.strategy.current_state.name}")
            if self.bot.last_minimap_frame is not None:
                self.minimap_widget.update_minimap(self.bot.last_minimap_frame)

    def _refresh_minimap(self):
        """Capture current frame and extract minimap region."""
        if self.bot is None:
            return
        frame = self.bot.screen.capture(self.bot.window.hwnd)
        if frame is None:
            return
        x, y, w, h = self.bot.minimap_region
        if w > 0 and h > 0:
            minimap = frame[y:y+h, x:x+w]
            self.minimap_widget.update_minimap(minimap)

    def _on_waypoints_changed(self, waypoints):
        """Update config and navigator when waypoints change."""
        if self.bot is not None:
            self.bot.config.patrol.waypoints = waypoints
            self.bot.navigator.set_waypoints(waypoints)

    def _save_waypoints(self):
        """Save current waypoints to config.yaml."""
        if self.bot is None:
            return
        waypoints = self.minimap_widget.get_waypoints()
        import yaml
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if "patrol" not in data:
                data["patrol"] = {}
            data["patrol"]["waypoints"] = waypoints
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            log.info("Waypoints saved: %d points", len(waypoints))
        except Exception as e:
            log.error("Failed to save waypoints: %s", e)

    def closeEvent(self, event):
        self._save_waypoints()
        if self.bot:
            self.bot.stop()
        event.accept()

    def _append_log(self, msg: str):
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )


def run_gui(config_path: str = "config.yaml"):
    """Launch the GUI application."""
    app = QApplication(sys.argv)
    window = BotWindow(config_path)
    window.show()
    sys.exit(app.exec_())

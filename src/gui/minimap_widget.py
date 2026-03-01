# src/gui/minimap_widget.py
"""Minimap widget for displaying minimap and editing waypoints."""

import logging
from typing import List

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont
from PyQt5.QtWidgets import QLabel

import numpy as np

logger = logging.getLogger("mirbot")


class MinimapWidget(QLabel):
    """Widget that displays the minimap and allows clicking to add waypoints."""

    waypoints_changed = pyqtSignal(list)  # emits list of [x, y] pairs

    def __init__(self, parent=None):
        super().__init__(parent)
        self._waypoints: List[List[int]] = []
        self._base_pixmap = None
        self._minimap_frame = None
        self.setMinimumSize(200, 220)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 1px solid #555; background: #111;")
        self.setText("点击刷新获取小地图")

    def update_minimap(self, frame: np.ndarray):
        """Update the displayed minimap image."""
        if frame is None or frame.size == 0:
            return
        self._minimap_frame = frame
        h, w = frame.shape[:2]
        # Convert BGR to RGB for Qt
        rgb = frame[:, :, ::-1].copy()
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        self._base_pixmap = QPixmap.fromImage(qimg)
        self._redraw()

    def set_waypoints(self, waypoints: List[List[int]]):
        """Set waypoints from config."""
        self._waypoints = [list(wp) for wp in waypoints]
        self._redraw()

    def get_waypoints(self) -> List[List[int]]:
        return self._waypoints

    def mousePressEvent(self, event):
        """Left click adds waypoint, right click removes nearest."""
        if self._base_pixmap is None:
            return

        pm = self.pixmap()
        if pm is None:
            return

        # Calculate offset (pixmap is centered in label)
        x_offset = (self.width() - pm.width()) // 2
        y_offset = (self.height() - pm.height()) // 2
        mx = event.x() - x_offset
        my = event.y() - y_offset

        if mx < 0 or my < 0 or mx >= pm.width() or my >= pm.height():
            return

        if event.button() == Qt.LeftButton:
            self._waypoints.append([mx, my])
            logger.info("Waypoint added: (%d, %d), total: %d", mx, my, len(self._waypoints))
        elif event.button() == Qt.RightButton:
            if self._waypoints:
                best_i = 0
                best_d = float("inf")
                for i, (wx, wy) in enumerate(self._waypoints):
                    d = (wx - mx) ** 2 + (wy - my) ** 2
                    if d < best_d:
                        best_d = d
                        best_i = i
                removed = self._waypoints.pop(best_i)
                logger.info("Waypoint removed: (%d, %d), remaining: %d",
                            removed[0], removed[1], len(self._waypoints))

        self.waypoints_changed.emit(self._waypoints)
        self._redraw()

    def clear_waypoints(self):
        self._waypoints.clear()
        self.waypoints_changed.emit(self._waypoints)
        self._redraw()

    def _redraw(self):
        """Redraw minimap with waypoints overlay."""
        if self._base_pixmap is None:
            return
        pm = self._base_pixmap.copy()
        painter = QPainter(pm)

        # Draw waypoint connections
        if len(self._waypoints) >= 2:
            pen = QPen(QColor(0, 255, 0, 180), 1)
            painter.setPen(pen)
            for i in range(len(self._waypoints) - 1):
                x1, y1 = self._waypoints[i]
                x2, y2 = self._waypoints[i + 1]
                painter.drawLine(x1, y1, x2, y2)
            # Close loop
            x1, y1 = self._waypoints[-1]
            x2, y2 = self._waypoints[0]
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(x1, y1, x2, y2)

        # Draw waypoint dots with numbers
        font = QFont("Arial", 7)
        painter.setFont(font)
        for i, (wx, wy) in enumerate(self._waypoints):
            painter.setPen(QPen(QColor(255, 255, 0), 1))
            painter.setBrush(QColor(255, 255, 0, 200))
            painter.drawEllipse(wx - 3, wy - 3, 6, 6)
            painter.setPen(QColor(255, 0, 0))
            painter.drawText(wx + 5, wy - 2, str(i + 1))

        painter.end()
        self.setPixmap(pm)

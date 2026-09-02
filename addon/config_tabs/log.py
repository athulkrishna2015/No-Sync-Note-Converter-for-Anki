import os
import subprocess
import sys
from pathlib import Path

from aqt.qt import *
from aqt.utils import showInfo, tooltip

from .. import logger


class LogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_size = -1
        self._last_mtime = 0
        self._watcher = None
        self._timer = None
        self._setup_ui()
        self._setup_watcher()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel(
            f"Debug log file: <b>{logger.get_log_file_path()}</b><br>"
            "All conversion, preset, mapping and error events are appended here for debugging. "
            "Logs are cleared on Anki start for a fresh session."
        )
        header.setWordWrap(True)
        header.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(header)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.log_view.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        layout.addWidget(self.log_view, 1)

        hint = QLabel(
            "Tip: Enable Live to tail the file. Use Refresh to reload, Clear to empty, Reveal to open the folder."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Live controls row
        live_row = QHBoxLayout()
        self.live_check = QCheckBox("Live (auto-refresh)")
        self.live_check.setChecked(True)
        self.live_check.setToolTip("When enabled, the view polls the log file and auto-updates.")
        self.live_check.toggled.connect(self._on_live_toggled)
        live_row.addWidget(self.live_check)

        self.live_interval = QSpinBox()
        self.live_interval.setRange(200, 5000)
        self.live_interval.setValue(800)
        self.live_interval.setSuffix(" ms")
        self.live_interval.setToolTip("Polling interval for Live mode")
        self.live_interval.valueChanged.connect(self._restart_timer)
        live_row.addWidget(QLabel("Interval:"))
        live_row.addWidget(self.live_interval)
        live_row.addStretch()
        self.live_status = QLabel("● Live")
        self.live_status.setStyleSheet("color: #2e7d32;")
        live_row.addWidget(self.live_status)
        layout.addLayout(live_row)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(refresh_btn)

        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_log)
        btn_row.addWidget(clear_btn)

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        btn_row.addWidget(copy_btn)

        reveal_btn = QPushButton("Reveal in File Manager")
        reveal_btn.clicked.connect(self.reveal_in_file_manager)
        btn_row.addWidget(reveal_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _setup_watcher(self):
        # Polling timer for live updates (lightweight, non-blocking)
        self._timer = QTimer(self)
        self._timer.setInterval(self.live_interval.value())
        self._timer.timeout.connect(self._poll_if_needed)
        if self.live_check.isChecked():
            self._timer.start()

        # QFileSystemWatcher for event-driven updates (best-effort)
        try:
            self._watcher = QFileSystemWatcher(self)
            log_path = str(logger.get_log_file_path())
            # Watch both file and parent dir (file may be recreated on clear/rotate)
            self._watcher.addPath(log_path)
            parent_dir = str(logger.get_log_file_path().parent)
            if parent_dir not in self._watcher.files() and parent_dir not in self._watcher.directories():
                self._watcher.addPath(parent_dir)
            self._watcher.fileChanged.connect(self._on_file_changed)
            self._watcher.directoryChanged.connect(self._on_dir_changed)
        except Exception:
            self._watcher = None

    def _on_live_toggled(self, checked: bool):
        self.live_status.setText("● Live" if checked else "○ Paused")
        self.live_status.setStyleSheet("color: #2e7d32;" if checked else "color: #9e9e9e;")
        self._restart_timer()

    def _restart_timer(self):
        if self._timer is None:
            return
        self._timer.stop()
        self._timer.setInterval(self.live_interval.value())
        if self.live_check.isChecked() and self.isVisible():
            self._timer.start()

    def _poll_if_needed(self):
        # Only poll when live and widget is visible to avoid background work
        if not self.live_check.isChecked() or not self.isVisible():
            return
        try:
            p = logger.get_log_file_path()
            if not p.exists():
                if self._last_size != -1:
                    self.refresh()
                return
            stat = p.stat()
            cur_size = stat.st_size
            cur_mtime = stat.st_mtime_ns
            # Quick check: size or mtime changed
            if cur_size != self._last_size or cur_mtime != self._last_mtime:
                self.refresh()
        except Exception:
            pass

    def _on_file_changed(self, path: str):
        # Re-add watcher if file was recreated (Qt removes it on delete)
        try:
            if path == str(logger.get_log_file_path()) and not os.path.exists(path):
                # File was cleared/truncated; will reappear
                QTimer.singleShot(200, self._readd_watcher)
            if self.live_check.isChecked():
                QTimer.singleShot(100, self.refresh)
        except Exception:
            pass

    def _on_dir_changed(self, path: str):
        self._readd_watcher()
        if self.live_check.isChecked():
            QTimer.singleShot(150, self._poll_if_needed)

    def _readd_watcher(self):
        if self._watcher is None:
            return
        try:
            log_path = str(logger.get_log_file_path())
            if os.path.exists(log_path) and log_path not in self._watcher.files():
                self._watcher.addPath(log_path)
            parent = str(logger.get_log_file_path().parent)
            if os.path.exists(parent) and parent not in self._watcher.directories() and parent not in self._watcher.files():
                self._watcher.addPath(parent)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._restart_timer()
        # Refresh on show if live, to catch changes while hidden
        if self.live_check.isChecked():
            QTimer.singleShot(50, self.refresh)

    def hideEvent(self, event):
        super().hideEvent(event)
        if self._timer is not None:
            self._timer.stop()

    def refresh(self):
        try:
            p = logger.get_log_file_path()
            if p.exists():
                stat = p.stat()
                self._last_size = stat.st_size
                self._last_mtime = stat.st_mtime_ns
            else:
                self._last_size = -1
                self._last_mtime = 0
        except Exception:
            self._last_size = -1

        text = logger.read_log_text()
        if not text:
            text = "(log empty)"

        # Preserve scroll position: only auto-scroll if already near bottom
        scrollbar = self.log_view.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 20

        self.log_view.setPlainText(text)

        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
            cursor = self.log_view.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_view.setTextCursor(cursor)

    def clear_log(self):
        result = QMessageBox.question(
            self,
            "Clear Debug Log",
            "Clear the debug log file? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        ok = logger.clear_log()
        if ok:
            tooltip("Log cleared.", parent=self)
            QTimer.singleShot(100, self.refresh)
        else:
            showInfo("Failed to clear log file.")

    def copy_to_clipboard(self):
        text = self.log_view.toPlainText()
        QApplication.clipboard().setText(text)
        tooltip("Log copied to clipboard.", parent=self)

    def reveal_in_file_manager(self):
        path = logger.get_log_file_path()
        try:
            folder = str(path.parent)
            if sys.platform.startswith("win"):
                os.startfile(folder)  # type: ignore
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            showInfo(f"Log folder: {folder}\n\nCould not open file manager: {e}")

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
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel(
            f"Debug log file: <b>{logger.get_log_file_path()}</b><br>"
            "All conversion, preset, mapping and error events are appended here for debugging."
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
            "Tip: Use Refresh to reload, Clear to empty the file, Reveal to open the folder."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

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

    def refresh(self):
        text = logger.read_log_text()
        if not text:
            text = "(log empty)"
        self.log_view.setPlainText(text)
        # Scroll to bottom
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
            self.refresh()
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

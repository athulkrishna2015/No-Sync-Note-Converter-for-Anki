from aqt.qt import *
from aqt.utils import tooltip
from aqt.webview import AnkiWebView

from .. import state


class SupportTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        support_hint = QLabel(
            "Support the addon with the payment methods below."
        )
        support_hint.setWordWrap(True)
        layout.addWidget(support_hint)

        support_scroll = QScrollArea()
        support_scroll.setWidgetResizable(True)
        support_content = QWidget()
        support_content_layout = QVBoxLayout(support_content)
        support_content_layout.setSpacing(16)

        for item in state.SUPPORT_ITEMS:
            support_content_layout.addWidget(self._create_support_item(item))

        support_content_layout.addStretch()
        support_scroll.setWidget(support_content)
        layout.addWidget(support_scroll, 1)

        # Ko-fi Widget (Embedded Script)
        self.support_webview = AnkiWebView(self)
        self.support_webview.setFixedHeight(40)
        kofi_html = f"""
        <html>
        <head>
        <style>
          body {{ background-color: transparent; margin: 0; padding: 0; overflow: hidden; }}
        </style>
        <script type='text/javascript' src='https://storage.ko-fi.com/cdn/widget/Widget_2.js'></script>
        <script type='text/javascript'>
          kofiwidget2.init('Support me on Ko-fi', '#72a4f2', 'D1D01W6NQT');
          kofiwidget2.draw();
        </script>
        </head>
        <body></body>
        </html>
        """
        self.support_webview.setHtml(kofi_html)
        layout.addWidget(self.support_webview)

    def _create_support_item(self, item):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(frame)
        layout.setSpacing(10)

        title = QLabel(item["label"])
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 1)
        title.setFont(title_font)
        layout.addWidget(title)

        value_row = QHBoxLayout()
        value_field = QLineEdit(item["value"])
        value_field.setReadOnly(True)
        value_field.setFont(
            QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        )
        value_field.setCursorPosition(0)
        value_row.addWidget(value_field, 1)

        copy_button = QPushButton(f"Copy {item['label']}")
        copy_button.clicked.connect(
            lambda _, label=item["label"], value=item["value"]: self._copy_support_value(
                label, value
            )
        )
        value_row.addWidget(copy_button)
        layout.addLayout(value_row)

        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(str(state.SUPPORT_DIR / item["image"]))
        if pixmap.isNull():
            qr_label.setText("QR code image not found.")
        else:
            scaled = pixmap.scaledToWidth(
                min(state.SUPPORT_QR_WIDTH, pixmap.width()),
                Qt.TransformationMode.SmoothTransformation,
            )
            qr_label.setPixmap(scaled)
            qr_label.setMinimumSize(scaled.size())

        qr_row = QHBoxLayout()
        qr_row.addStretch()
        qr_row.addWidget(qr_label)
        qr_row.addStretch()
        layout.addLayout(qr_row)

        return frame

    def _copy_support_value(self, label, value):
        QApplication.clipboard().setText(value)
        tooltip(f"{label} ID copied.", parent=self)

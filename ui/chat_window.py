"""Floating Compact Top-Right HUD Chat Window for Iris."""

import html
import re
from typing import Dict, List, Optional
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import (
    QTextCursor,
    QGuiApplication,
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QPlainTextEdit,
    QFrame,
)
from config import config


def format_markdown_to_rich_html(raw_text: str) -> str:
    """Converts markdown, ASCII charts, code blocks, and lists to styled HTML."""
    if not raw_text:
        return ""

    escaped = html.escape(raw_text)

    # 1. Code blocks ```lang ... ```
    def replace_code_block(match):
        code_content = match.group(1).strip()
        return (
            f'<div style="background-color: #0d1117; border: 1px solid #30363d; '
            f'border-radius: 6px; padding: 8px 10px; margin: 6px 0; font-family: Consolas, monospace; '
            f'font-size: 11px; color: #58a6ff; white-space: pre-wrap;">{code_content}</div>'
        )

    escaped = re.sub(r"```(?:\w+)?\n([\s\S]*?)```", replace_code_block, escaped)

    # 2. Inline code `...`
    escaped = re.sub(
        r"`([^`]+)`",
        r'<code style="background-color: #1f2937; color: #38bdf8; padding: 2px 4px; '
        r'border-radius: 4px; font-family: Consolas, monospace; font-size: 11px;">\1</code>',
        escaped,
    )

    # 3. Detect ASCII diagrams / box drawing sections
    box_pattern = r"([┌┐└┘├┤┬┴┼─│═║╔╗╚╝╠╣╦╩╬▀▄█▌▐░▒▓■□▪▫▲▼▶◀◆◇\+\-\|]{3,}[\s\S]*?(?:\n\n|\Z))"

    def replace_ascii_box(match):
        box_text = match.group(1).strip()
        return (
            f'<div style="background-color: #0b1329; border: 1px solid #1e3a8a; '
            f'border-radius: 6px; padding: 8px 10px; margin: 6px 0; font-family: Consolas, monospace; '
            f'font-size: 11px; color: #38bdf8; white-space: pre;">{box_text}</div>'
        )

    escaped = re.sub(box_pattern, replace_ascii_box, escaped)

    # 4. Bold & Italic
    escaped = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color: #f8fafc;">\1</strong>', escaped)
    escaped = re.sub(r"\*([^*]+)\*", r'<em style="color: #cbd5e1;">\1</em>', escaped)

    # 5. Bullet points & lines
    escaped = re.sub(r"^\s*[\*\-]\s+(.+)$", r'<div style="margin: 2px 0 2px 8px;">• \1</div>', escaped, flags=re.MULTILINE)
    escaped = re.sub(r"^\s*(\d+)\.\s+(.+)$", r'<div style="margin: 2px 0 2px 8px;"><b>\1.</b> \2</div>', escaped, flags=re.MULTILINE)

    # 6. Line breaks
    escaped = escaped.replace("\n", "<br/>")

    return escaped


class ChatInputEdit(QPlainTextEdit):
    """Auto-submitting text input with Shift+Enter support for multiline."""

    return_pressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.setPlaceholderText("Ask Iris or type /act, /goal, /speak...")
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #111827;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QPlainTextEdit:focus {
                border: 1px solid #38bdf8;
                background-color: #0f172a;
            }
        """)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.return_pressed.emit()
        else:
            super().keyPressEvent(event)


class FloatingChatWindow(QWidget):
    """Compact floating HUD chat window docked at top-right with scrollable history and rich formatting."""

    message_submitted = Signal(str)
    voice_toggled = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Frameless, Stays on Top, Tool Window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._drag_pos = QPoint()
        self.messages: List[Dict[str, str]] = []

        self._init_ui()
        self._position_top_right()
        self._render_all_messages()

    def _init_ui(self) -> None:
        """Initializes the glassmorphic dark interface without negative shadow bounds."""
        self.setFixedSize(config.ui_width, config.ui_height)

        # Root Card Frame with styled glowing border
        self.card = QFrame(self)
        self.card.setGeometry(0, 0, self.width(), self.height())
        self.card.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1.5px solid #38bdf8;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 1. Header Bar
        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 2, 0)

        # Title & Badge
        self.title_label = QLabel("✨ Iris HUD")
        self.title_label.setStyleSheet("""
            font-family: 'Segoe UI', sans-serif;
            font-size: 13px;
            font-weight: bold;
            color: #38bdf8;
            border: none;
            background: transparent;
        """)
        header.addWidget(self.title_label)

        # Status badge
        self.status_badge = QLabel("READY")
        self.status_badge.setStyleSheet("""
            font-family: 'Segoe UI', sans-serif;
            font-size: 9px;
            font-weight: bold;
            color: #10b981;
            background-color: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.4);
            border-radius: 4px;
            padding: 2px 6px;
        """)
        header.addWidget(self.status_badge)
        header.addStretch()

        # Close / Hide Button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: none;
                font-size: 12px;
                font-weight: bold;
                border-radius: 11px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
                color: #ef4444;
            }
        """)
        self.close_btn.clicked.connect(self.hide)
        header.addWidget(self.close_btn)

        layout.addLayout(header)

        # 2. Scrollable Message Browser
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #0b0f19;
                color: #e2e8f0;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QScrollBar:vertical {
                border: none;
                background: #0f172a;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #38bdf8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        layout.addWidget(self.browser)

        # 3. Bottom Input Row
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        # Text input
        self.input_edit = ChatInputEdit(self)
        self.input_edit.return_pressed.connect(self._on_send_clicked)
        input_row.addWidget(self.input_edit)

        # Voice Mic Button
        self.mic_btn = QPushButton("🎙")
        self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.setToolTip("Toggle Voice Listening")
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
            }
        """)
        self.mic_btn.clicked.connect(self.voice_toggled.emit)
        input_row.addWidget(self.mic_btn)

        # Send Button
        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(36, 36)
        self.send_btn.setToolTip("Send Message (Enter)")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0ea5e9;
            }
            QPushButton:pressed {
                background-color: #0369a1;
            }
        """)
        self.send_btn.clicked.connect(self._on_send_clicked)
        input_row.addWidget(self.send_btn)

        layout.addLayout(input_row)

    def _position_top_right(self) -> None:
        """Positions the HUD in the top-right quadrant with margin."""
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.right() - self.width() - config.ui_right_margin
            y = geo.top() + config.ui_top_margin
            self.move(x, y)

    def mousePressEvent(self, event):
        """Allow dragging the window by clicking on header area."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = QPoint()

    def set_status(self, text: str, mode: str = "ready") -> None:
        """Updates top status pill."""
        self.status_badge.setText(text.upper())
        if mode == "listening":
            self.status_badge.setStyleSheet("""
                font-size: 9px; font-weight: bold; color: #38bdf8;
                background-color: rgba(56, 189, 248, 0.2);
                border: 1px solid #38bdf8; border-radius: 4px; padding: 2px 6px;
            """)
        elif mode == "thinking":
            self.status_badge.setStyleSheet("""
                font-size: 9px; font-weight: bold; color: #a855f7;
                background-color: rgba(168, 85, 247, 0.2);
                border: 1px solid #a855f7; border-radius: 4px; padding: 2px 6px;
            """)
        elif mode == "speaking":
            self.status_badge.setStyleSheet("""
                font-size: 9px; font-weight: bold; color: #f59e0b;
                background-color: rgba(245, 158, 11, 0.2);
                border: 1px solid #f59e0b; border-radius: 4px; padding: 2px 6px;
            """)
        else:
            self.status_badge.setStyleSheet("""
                font-size: 9px; font-weight: bold; color: #10b981;
                background-color: rgba(16, 185, 129, 0.15);
                border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 4px; padding: 2px 6px;
            """)

    def _on_send_clicked(self) -> None:
        text = self.input_edit.toPlainText().strip()
        if not text:
            return
        self.input_edit.clear()
        self.add_user_message(text)
        self.message_submitted.emit(text)

    def add_user_message(self, text: str) -> None:
        """Adds styled user speech bubble."""
        self.messages.append({"role": "user", "content": text})
        self._render_all_messages()

    def start_assistant_message(self) -> None:
        """Prepares for streaming assistant response."""
        self.messages.append({"role": "assistant", "content": ""})
        self.set_status("Thinking...", "thinking")
        self._render_all_messages()

    def append_assistant_chunk(self, chunk: str) -> None:
        """Streams chunk and updates current message."""
        if self.messages and self.messages[-1]["role"] == "assistant":
            self.messages[-1]["content"] += chunk
        else:
            self.messages.append({"role": "assistant", "content": chunk})
        self._render_all_messages()

    def finish_assistant_message(self, full_text: Optional[str] = None) -> None:
        """Finalizes the assistant message."""
        if full_text is not None:
            if self.messages and self.messages[-1]["role"] == "assistant":
                self.messages[-1]["content"] = full_text
            else:
                self.messages.append({"role": "assistant", "content": full_text})
        self._render_all_messages()
        self.set_status("Ready", "ready")

    def _render_all_messages(self) -> None:
        """Renders entire conversation history with zero undo/cursor glitches."""
        html_parts = [
            '<div style="margin: 4px 0 10px 0; background-color: rgba(30, 41, 59, 0.7); '
            'border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 8px; padding: 8px 10px; '
            'font-size: 11px; color: #cbd5e1;">'
            '👋 <b>Welcome to Iris HUD</b><br/>'
            '<span style="color:#94a3b8; font-size:10.5px;">'
            'Press <code>Ctrl+Shift+T</code> to toggle. Type your prompt, execute <code>/goal</code>, '
            'or say <b>"Hey Iris"</b> for voice.</span>'
            '</div>'
        ]

        for msg in self.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                escaped = html.escape(content).replace("\n", "<br/>")
                html_parts.append(
                    f'<div style="margin: 8px 0; text-align: right;">'
                    f'<div style="display: inline-block; background-color: #1e293b; color: #f1f5f9; '
                    f'border: 1px solid #334155; border-radius: 10px 10px 2px 10px; padding: 7px 12px; '
                    f'max-width: 85%; text-align: left; font-size: 12px;">'
                    f'{escaped}'
                    f'</div>'
                    f'</div>'
                )
            elif role == "assistant":
                rich_content = format_markdown_to_rich_html(content)
                html_parts.append(
                    f'<div style="margin: 8px 0; text-align: left;">'
                    f'<div style="display: inline-block; background-color: #0f172a; color: #e2e8f0; '
                    f'border: 1px solid #1e3a8a; border-radius: 10px 10px 10px 2px; padding: 8px 12px; '
                    f'max-width: 95%; font-size: 12px; line-height: 1.4;">'
                    f'<span style="color:#38bdf8; font-weight:bold; font-size:11px;">IRIS</span><br/>'
                    f'{rich_content}'
                    f'</div>'
                    f'</div>'
                )
            elif role == "system":
                html_parts.append(
                    f'<div style="margin: 6px 0; background-color: rgba(30, 41, 59, 0.6); '
                    f'border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 8px; padding: 8px 10px; '
                    f'font-size: 11px; color: #cbd5e1;">'
                    f'{content}'
                    f'</div>'
                )

        full_html = (
            f'<body style="background-color: #0b0f19; font-family: Segoe UI, sans-serif; margin: 0; padding: 0;">'
            f'{"".join(html_parts)}'
            f'</body>'
        )
        self.browser.setHtml(full_html)
        self.browser.moveCursor(QTextCursor.MoveOperation.End)

    def toggle_visibility(self) -> None:
        """Toggles show/hide with position verification."""
        if self.isVisible():
            self.hide()
        else:
            self._position_top_right()
            self.show()
            self.raise_()
            self.activateWindow()
            self.input_edit.setFocus()

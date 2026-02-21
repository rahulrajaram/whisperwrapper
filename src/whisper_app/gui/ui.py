"""UI builder helpers for WhisperGUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QHeaderView

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .main_window import WhisperGUI


def build_main_interface(gui: "WhisperGUI") -> None:
    central_widget = QWidget()
    gui.setCentralWidget(central_widget)

    main_layout = QVBoxLayout()
    central_widget.setLayout(main_layout)

    title = QLabel("🎤 Whisper Voice Recording")
    title_font = QFont()
    title_font.setPointSize(14)
    title_font.setBold(True)
    title.setFont(title_font)
    main_layout.addWidget(title)

    button_layout = QHBoxLayout()

    gui.start_button = QPushButton("▶")
    gui.start_button.setToolTip("Start Recording")
    gui.start_button_style_normal = """
        QPushButton {
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            padding: 10px;
            border-radius: 5px;
            min-width: 50px;
            min-height: 50px;
            font-size: 24px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
    """
    gui.start_button_style_inactive = """
        QPushButton {
            background-color: #cccccc;
            color: #888888;
            font-weight: bold;
            padding: 10px;
            border-radius: 5px;
            min-width: 50px;
            min-height: 50px;
            font-size: 24px;
        }
        QPushButton:hover {
            background-color: #cccccc;
        }
    """
    gui.start_button.setStyleSheet(gui.start_button_style_normal)
    gui.start_button.clicked.connect(gui.start_recording)
    button_layout.addWidget(gui.start_button)

    gui.stop_button = QPushButton("⏹")
    gui.stop_button.setToolTip("Stop Recording")
    gui.stop_button_style_inactive = """
        QPushButton {
            background-color: #cccccc;
            color: #888888;
            font-weight: bold;
            padding: 10px;
            border-radius: 5px;
            min-width: 50px;
            min-height: 50px;
            font-size: 24px;
        }
        QPushButton:hover {
            background-color: #cccccc;
        }
    """
    gui.stop_button_style_active = """
        QPushButton {
            background-color: #f44336;
            color: white;
            font-weight: bold;
            padding: 10px;
            border-radius: 5px;
            min-width: 50px;
            min-height: 50px;
            font-size: 24px;
        }
        QPushButton:hover {
            background-color: #da190b;
        }
        QPushButton:pressed {
            background-color: #ba0000;
        }
    """
    gui.stop_button.setStyleSheet(gui.stop_button_style_inactive)
    gui.stop_button.clicked.connect(gui.stop_recording)
    button_layout.addWidget(gui.stop_button)

    gui.clear_button = QPushButton("🗑")
    gui.clear_button.setToolTip("Clear History")
    gui.clear_button.setStyleSheet(
        """
        QPushButton {
            background-color: #FF9800;
            color: white;
            font-weight: bold;
            padding: 10px;
            border-radius: 5px;
            min-width: 50px;
            min-height: 50px;
            font-size: 24px;
        }
        QPushButton:hover {
            background-color: #e68900;
        }
    """
    )
    gui.clear_button.clicked.connect(gui.clear_history)
    button_layout.addWidget(gui.clear_button)

    gui.codex_button = QPushButton("✨")
    gui.codex_button.setToolTip("Process with Claude (highlight keywords & fix typos)")
    gui.codex_button_style_normal = """
        QPushButton {
            background-color: #9C27B0;
            color: white;
            font-weight: bold;
            padding: 10px;
            border-radius: 5px;
            min-width: 50px;
            min-height: 50px;
            font-size: 24px;
        }
        QPushButton:hover {
            background-color: #7B1FA2;
        }
    """
    gui.codex_button_style_processing = """
        QPushButton {
            background-color: #cccccc;
            color: #888888;
            font-weight: bold;
            padding: 10px;
            border-radius: 5px;
            min-width: 50px;
            min-height: 50px;
            font-size: 24px;
        }
    """
    gui.codex_button.setStyleSheet(gui.codex_button_style_normal)
    gui.codex_button.clicked.connect(gui.on_codex_button_clicked)
    button_layout.addWidget(gui.codex_button)

    gui.terminal_button = QPushButton("💻")
    gui.terminal_button.setToolTip("Open Terminal in Project Directory")
    gui.terminal_button_style = """
        QPushButton {
            background-color: #1976D2;
            color: white;
            font-weight: bold;
            padding: 10px;
            border-radius: 5px;
            min-width: 50px;
            min-height: 50px;
            font-size: 24px;
        }
        QPushButton:hover {
            background-color: #1565C0;
        }
        QPushButton:pressed {
            background-color: #0D47A1;
        }
    """
    gui.terminal_button.setStyleSheet(gui.terminal_button_style)
    gui.terminal_button.clicked.connect(gui.on_terminal_button_clicked)
    button_layout.addWidget(gui.terminal_button)

    gui.settings_button = QPushButton("⚙️")
    gui.settings_button.setToolTip("Microphone Settings")
    gui.settings_button_style = """
        QPushButton {
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            padding: 10px;
            border-radius: 5px;
            min-width: 50px;
            min-height: 50px;
            font-size: 20px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
    """
    gui.settings_button.setStyleSheet(gui.settings_button_style)
    gui.settings_button.clicked.connect(gui.on_settings_button_clicked)
    button_layout.addWidget(gui.settings_button)

    button_layout.addStretch()
    main_layout.addLayout(button_layout)

    gui.status_label = QLabel("Ready")
    main_layout.addWidget(gui.status_label)

    history_label = QLabel("📝 Transcription History")
    history_font = QFont()
    history_font.setBold(True)
    history_label.setFont(history_font)
    main_layout.addWidget(history_label)

    gui.history_table = QTableWidget()
    gui.history_table.setColumnCount(4)
    gui.history_table.setHorizontalHeaderLabels(["Timestamp", "Transcription", "Copy", "Lock"])
    gui.history_table.setColumnWidth(0, 180)
    gui.history_table.setColumnWidth(1, 550)
    gui.history_table.setColumnWidth(2, 60)
    gui.history_table.setColumnWidth(3, 60)
    gui.history_table.setWordWrap(True)
    gui.history_table.verticalHeader().setDefaultSectionSize(60)
    gui.history_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    gui.history_table.cellClicked.connect(gui.on_table_cell_clicked)
    main_layout.addWidget(gui.history_table)

    gui.statusBar().showMessage("Ready")


def configure_tray(gui: "WhisperGUI") -> None:
    gui.tray_icon = QSystemTrayIcon(gui)
    try:
        gui.tray_icon_green = QIcon.fromTheme("media-playback-start")
        gui.tray_icon_red = QIcon.fromTheme("media-record")
        gui.tray_icon_yellow = QIcon.fromTheme("media-playback-pause")
    except Exception:  # pragma: no cover - depends on desktop env
        gui.tray_icon_green = gui.tray_icon_red = gui.tray_icon_yellow = None

    gui._set_tray_icon_green()
    tray_menu = QMenu()

    show_action = tray_menu.addAction("Show/Hide")
    show_action.triggered.connect(gui.toggle_window)

    tray_menu.addSeparator()
    gui.tray_status = tray_menu.addAction("🎤 Ready")
    gui.tray_status.setEnabled(False)

    tray_menu.addSeparator()
    start_action = tray_menu.addAction("▶ Start Recording")
    start_action.triggered.connect(gui.start_recording)
    stop_action = tray_menu.addAction("⏹ Stop Recording")
    stop_action.triggered.connect(gui.stop_recording)

    tray_menu.addSeparator()
    exit_action = tray_menu.addAction("Exit")
    exit_action.triggered.connect(gui.exit_app)

    gui.tray_icon.setContextMenu(tray_menu)
    gui.tray_icon.show()
    gui.tray_icon.activated.connect(gui.tray_icon_activated)

"""GUI action helpers (dialogs, terminal launchers)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .main_window import WhisperGUI


def open_project_terminal(gui: "WhisperGUI") -> None:
    project_dir = str(Path(__file__).parent.parent.absolute())
    terminal_commands = [
        (["/usr/bin/xfce4-terminal", "--working-directory", project_dir], "xfce4-terminal"),
        (["xfce4-terminal", "--working-directory", project_dir], "xfce4-terminal"),
        (["/usr/bin/konsole", "-e", f"bash -c 'cd {project_dir} && bash'"], "konsole"),
        (["konsole", "-e", f"bash -c 'cd {project_dir} && bash'"], "konsole"),
        (["/usr/bin/gnome-terminal", "--working-directory", project_dir], "gnome-terminal"),
        (["gnome-terminal", "--working-directory", project_dir], "gnome-terminal"),
        (["/usr/bin/xterm", "-e", f"cd {project_dir}; bash"], "xterm"),
        (["xterm", "-e", f"cd {project_dir}; bash"], "xterm"),
    ]

    terminal_found = False
    for cmd, name in terminal_commands:
        try:
            import subprocess

            subprocess.Popen(cmd, start_new_session=True)
            gui.statusBar().showMessage(f"📂 Terminal ({name}) opened in: {project_dir}")
            terminal_found = True
            break
        except (FileNotFoundError, OSError):
            continue

    if not terminal_found:
        error_msg = "❌ No terminal found (tried xfce4-terminal, konsole, gnome-terminal, xterm)"
        gui.statusBar().showMessage(error_msg)
        gui.status_label.setText(error_msg)


def show_microphone_settings(gui: "WhisperGUI") -> None:
    from PyQt6.QtWidgets import QComboBox, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

    try:
        audio_service = gui.recording_controller.audio_service
        devices = audio_service.list_input_devices()
        if not devices:
            gui.status_label.setText("❌ No input devices found")
            return

        dialog = QDialog(gui)
        dialog.setWindowTitle("Microphone Settings")
        dialog.setGeometry(200, 200, 500, 150)

        layout = QVBoxLayout(dialog)
        label = QLabel("Select microphone input device:")
        layout.addWidget(label)

        combo = QComboBox()
        for device in devices:
            combo.addItem(device.name, device.index)

        current_device = audio_service.input_device_index
        if current_device is not None:
            for idx, device in enumerate(devices):
                if device.index == current_device:
                    combo.setCurrentIndex(idx)
                    break

        layout.addWidget(combo)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")

        def save_settings():
            selected_index = combo.currentIndex()
            device_idx = combo.itemData(selected_index)
            audio_service.input_device_index = device_idx
            gui.status_label.setText(
                f"✅ Microphone set to: {combo.currentText()}"
            )
            gui.statusBar().showMessage("Microphone settings saved")
            dialog.accept()

        ok_button.clicked.connect(save_settings)
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.exec()

    except Exception as exc:  # pragma: no cover - depends on PyQt internals
        gui.status_label.setText(f"❌ Error: {exc}")
        gui.statusBar().showMessage("Failed to access audio devices")

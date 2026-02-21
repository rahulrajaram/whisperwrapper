"""Worker thread to invoke the Claude CLI."""

from __future__ import annotations

import subprocess
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal


class CodexWorker(QObject):
    """Worker thread for Claude CLI processing."""

    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(str, int)

    def __init__(self, text: str, row_index: int = 0):
        super().__init__()
        self.text = text
        self.row_index = row_index

    def run(self) -> None:
        try:
            prompt = f"""IMPORTANT: Return ONLY the processed text. No explanations, no preamble, no extra text.\n\nProcess this transcription:\n- Highlight the most important keywords (up to 10% of text) with **keyword** format\n- Fix any obvious typos\n- Return ONLY the processed text, nothing else\n\nTranscription:\n{self.text}"""

            process = subprocess.Popen(
                ["claude"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = process.communicate(input=prompt, timeout=60)

            if process.returncode == 0 and stdout:
                output = stdout.strip()
                processed_text = self._extract_processed_line(output)
                self.result.emit(processed_text or output, self.row_index)
            else:
                error_msg = stderr if stderr else "Unknown error from Claude"
                self.error.emit(f"Claude processing failed: {error_msg}")

            self.finished.emit()
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except Exception:  # pragma: no cover - best effort cleanup
                pass
            self.error.emit("Claude processing timed out (exceeded 60 seconds).")
            self.finished.emit()
        except FileNotFoundError:
            self.error.emit("Claude CLI not found. Is it installed and in PATH?")
            self.finished.emit()
        except Exception as exc:  # pragma: no cover - safety net
            self.error.emit(f"Error processing with Claude: {exc}")
            self.finished.emit()

    def _extract_processed_line(self, output: str) -> Optional[str]:
        lines = output.split('\n')
        for line in reversed(lines):
            stripped = line.strip()
            if stripped and ("**" in stripped or len(stripped) > 10):
                return stripped
        return None

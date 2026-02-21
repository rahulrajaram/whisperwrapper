"""General GUI utilities."""

from __future__ import annotations

import re


def markdown_to_html(text: str) -> str:
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)


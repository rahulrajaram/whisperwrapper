# Transcript and recipe launcher

Whisper Voice owns a keyboard-driven launcher over persisted transcript history
and declarative command recipes. External controls open it on the Transcript
History tab by sending the `history` command:

```sh
whisper-recording-toggle history
```

The picker captures the currently active X11 window before taking focus. Its
controls are:

- keypad `8` / `2` or arrow keys: move up / down;
- keypad `9` / `3` or Page Up / Page Down: move by page;
- Tab, or macropad `4` / `6`: switch between Transcript History and Recipes;
- Enter: copy the selected transcript, restore the captured window, and paste
  at its existing caret, or launch the selected recipe;
- Ctrl+C: copy and restore focus without pasting;
- Escape: cancel and restore focus;
- ordinary typing: filter by timestamp or transcript text.

Recipe searches include their title, description, keywords, and command. A
selected recipe opens a new held XFCE Terminal in its configured working
directory. Commands are represented as argument arrays and executed without a
shell; multiple arrays run sequentially and stop at the first failure.

The packaged catalog is `src/whisper_app/recipes.json`. Optional per-machine
recipes belong in `~/.config/whisper/recipes.json`; entries there override
packaged recipes with the same `id`. Set `WHISPER_RECIPE_CATALOG` to use a
different per-machine catalog. The initial packaged recipes are:

- **DeepMetrics — Continue development:** launches an interactive Codex session
  in `~/Documents/deepmetrics`;
- **DeepMetrics — System health summary:** runs
  `venv/bin/python -m deepmetrics --summary --no-bpf` in a new terminal.

Transcript contents remain in `~/.whisper/gui_history.json`; callers receive no
history data. The history file is restricted to the owning account (`0600`)
when loaded or saved.

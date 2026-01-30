# Expression2 EGP Generator (Modern HUD Designer)

A modern, dark-themed HUD layout tool for Garry's Mod EGP / Expression2. It behaves like a lightweight drawing app with layers, tools, zoom/pan, and project save/load.

## Features
- Tools: select, line (variable thickness), rectangle (outline), box (filled), circle (outline/filled), polygon, text
- Layers: add, duplicate, rename, reorder, show/hide, lock, color override
- Project save/load (`.e2hud.json`)
- Export to as a `.txt` file or copy to clipboard
- Zoom/pan and resolution presets
- Resolution scaling: export adapts to any screen size using your project aspect ratio

## Run
```bash
python main.py
```

## Build EXE (Windows)
This uses PyInstaller.

```powershell
python -m pip install --upgrade pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "E2-HUD-Designer" main.py
```

The EXE will be created in `dist/`.

## Controls
- Left click to draw or select
- Drag with Select to box-select multiple shapes
- Double click (or Enter) to finish polygons
- Delete/Backspace to remove selected shapes
- Ctrl to snap to grid + text edges
- Shift while moving or dragging vertices locks to horizontal/vertical
- Drag polygon points (Select tool) to edit vertices
- Ctrl+Z to undo
- Ctrl+C / Ctrl+V to copy/paste shapes (disabled while typing in fields)
- Right or middle mouse drag to pan
- Mouse wheel to zoom

## Dynamic Text Inputs
Define inputs in the Inputs panel as `NAME:TYPE`, where `TYPE` is `Normal` or `String`.

In text, use tokens:
- `%NAME%` inserts the value
- `%NAME%R1` rounds to 1 decimal (Normal only)

Dynamic text is updated every 100ms in a `if(clk()) { interval(100) }` block.

## Export Notes
- Uses `EGP:` wirelink (e.g. `EGP:egpBox(...)`).
- Dynamic text uses `EGP:egpSetText(...)`.
- Text alignment is exported with `EGP:egpAlign(id, horiz, vert)`; vert defaults to middle.
- Output scales to the current screen size using the project resolution as the reference.

## UI Notes
- Default font size is 18 in-game, displayed at half size in the editor (9) to account for strange font behaviours here.

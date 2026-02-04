# Expression2 HUD Creation Kit

A standalone, no-context HUD layout editor for Garry's Mod Expression2 EGP. This is a lightweight, dark-themed drawing app focused on building HUDs from preset primitives and exporting ready-to-paste E2 code. No extra setup beyond Python is required.

## What This Is
- A desktop editor for assembling HUD layouts from shapes and text.
- A project format you can save/load and keep iterating on.
- An exporter that outputs E2 EGP code using a normalized `EGP:` wirelink style.

## Key Features
- **Tools:** Select, Line, Rect (outline), Box (filled), Circle (outline), Circle+ (filled), Poly, Text
- **Selection:** click select, box select, multi-select, live selection center, delete, mirror X/Y
- **Editing:** drag vertices, snap to grid/text edges with Ctrl, axis-lock with Shift
- **Layers:** add/duplicate/rename/reorder, show/hide, lock, color override
- **Grid + View:** zoom, pan, fit-to-view, resolution presets, project-scaled output
- **Project I/O:** save/load `.e2hud.json`, export to file or copy to clipboard
- **Dynamic Text:** `%NAME%` and `%NAME%R1` token support with 100ms updates

## Run
```bash
python main.py
```

## Build EXE (Windows)
This uses PyInstaller.

```powershell
python -m pip install --upgrade pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "e2_hud_designer_v1.1-alpha" main.py
```

The EXE is written to `dist/`.

## Controls (Quick)
- **Left click** to draw or select
- **Drag** with Select to box-select
- **Double click / Enter** to finish polygons
- **Delete / Backspace** deletes selection
- **Ctrl** snaps to grid + text edges (and resizes circles from center)
- **Shift** locks movement to horizontal/vertical while moving or dragging vertices
- **Ctrl+Z** undo
- **Ctrl+C / Ctrl+V** copy/paste (disabled while typing in fields)
- **Right or Middle drag** to pan
- **Mouse wheel** to zoom

## Dynamic Inputs
Add inputs in the Inputs panel as `NAME:TYPE`:
- `TYPE` is `Normal` (double) or `String`

Text tokens:
- `%NAME%` inserts the value
- `%NAME%R1` rounds to 1 decimal (Normal only)

Dynamic text is updated every 100ms via a `if(clk()) { interval(100) }` block.

## Export Notes
- Uses the `EGP:` wirelink style (e.g., `EGP:egpBox(...)`).
- Dynamic text uses `EGP:egpSetText(...)`.
- Text alignment uses `EGP:egpAlign(id, horiz, vert)` (vertical defaults to middle).
- Output scales to the current screen size using the project resolution as the reference.

## UI Notes
- Default in-game font size is 18; it's displayed at half size in the editor (9) for better parity.

# Configuration values for the E2 HUD designer.

WINDOW_TITLE = "E2 HUD Designer"

# Common HUD resolutions (width, height)
RESOLUTION_PRESETS = [
    (1280, 720),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
    (3440, 1440),
    (3840, 2160),
]

DEFAULT_RESOLUTION = (1920, 1080)

HUD_FILE = "Hud.txt"
PROJECT_EXTENSION = ".e2hud.json"

COLORS = [
    "#E6E6E6",
    "#FFFFFF",
    "#0A0A0A",
    "#FF4D4D",
    "#FF9500",
    "#FFD60A",
    "#32D74B",
    "#0A84FF",
    "#64D2FF",
    "#BF5AF2",
    "#FF2D55",
]

FONTS = [
    "Segoe UI",
    "Calibri",
    "Arial",
    "Consolas",
]

DEFAULT_FONT = "Segoe UI"

THEME = {
    "bg": "#1F2125",
    "panel": "#262A30",
    "panel_alt": "#2F343C",
    "text": "#E6E6E6",
    "muted": "#9AA0A6",
    "accent": "#0A84FF",
    "accent_alt": "#64D2FF",
    "danger": "#FF4D4D",
    "grid": "#323741",
    "grid_super": "#414752",
    "grid_major": "#575D67",
    "grid_base": "#6F757F",
    "grid_center": "#B7BCC3",
}

GRID_MAJOR_STEP = 120
GRID_MINOR_STEP = 25

DEFAULT_STROKE = "#E6E6E6"
DEFAULT_FILL = "#0A84FF"
DEFAULT_STROKE_WIDTH = 2
DEFAULT_FONT_SIZE = 18
DEFAULT_TEXT = "HUD"

ZOOM_MIN = 0.1
ZOOM_MAX = 6.0
ZOOM_STEP = 1.1

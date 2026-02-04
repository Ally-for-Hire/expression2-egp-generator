# Canvas interaction and EGP shape creation.

from __future__ import annotations

from typing import Callable, List, Tuple

import tkinter as tk
from matplotlib import colors

import config
from exporter import HudExporter


class CanvasController:
    def __init__(
        self,
        master: tk.Tk,
        exporter: HudExporter,
        get_color: Callable[[], str],
        get_shape_type: Callable[[], str],
        snap_amount: int,
    ) -> None:
        """Description: Init
        Inputs: master: tk.Tk, exporter: HudExporter, get_color: Callable[[], str], get_shape_type: Callable[[], str], snap_amount: int
        """
        self._exporter = exporter
        self._get_color = get_color
        self._get_shape_type = get_shape_type
        self._snap_amount = snap_amount

        self.canvas = tk.Canvas(master, width=config.CANVAS_WIDTH, height=config.CANVAS_HEIGHT)
        self.canvas.bind("<Button-1>", self.on_click)

        self._points: List[Tuple[float, float]] = []
        self._shape_items: List[int] = []
        self._grid_items: List[int] = []

    @property
    def shape_count(self) -> int:
        """Description: Shape count
        Inputs: None
        """
        return len(self._shape_items)

    def set_snap_amount(self, amount: int) -> None:
        """Description: Set snap amount
        Inputs: amount: int
        """
        self._snap_amount = amount

    def draw_grid(self, grid_size: int) -> None:
        """Description: Draw grid
        Inputs: grid_size: int
        """
        for item_id in self._grid_items:
            self.canvas.delete(item_id)
        self._grid_items.clear()

        hig = int(config.CANVAS_HEIGHT / grid_size)
        wig = int(config.CANVAS_WIDTH / grid_size)
        for i in range(wig):
            self._grid_items.append(
                self.canvas.create_rectangle(
                    i * grid_size - 5,
                    0,
                    i * grid_size - 5,
                    config.CANVAS_WIDTH,
                    fill=config.GRID_LINE_COLOR,
                    outline=config.GRID_LINE_COLOR,
                )
            )
        for i in range(hig):
            self._grid_items.append(
                self.canvas.create_rectangle(
                    0,
                    i * grid_size,
                    config.CANVAS_WIDTH,
                    i * grid_size,
                    fill=config.GRID_LINE_COLOR,
                    outline=config.GRID_LINE_COLOR,
                )
            )

        self.canvas.create_rectangle(-config.CANVAS_WIDTH, -config.CANVAS_HEIGHT, config.CANVAS_WIDTH, config.CANVAS_HEIGHT)
        self.canvas.create_line(
            -config.CANVAS_WIDTH,
            config.CANVAS_HEIGHT / 2,
            config.CANVAS_WIDTH,
            config.CANVAS_HEIGHT / 2,
            dash=config.GRID_DASH,
            fill=config.GRID_CENTER_COLOR,
        )
        self.canvas.create_line(
            config.CANVAS_WIDTH / 2,
            -config.CANVAS_HEIGHT,
            config.CANVAS_WIDTH / 2,
            config.CANVAS_HEIGHT,
            dash=config.GRID_DASH,
            fill=config.GRID_CENTER_COLOR,
        )

        for item_id in self._shape_items:
            self.canvas.tag_raise(item_id)

    def undo_last(self) -> None:
        """Description: Undo last
        Inputs: None
        """
        if not self._shape_items:
            print("Nothing to undo")
            return
        last_index = len(self._shape_items) - 1
        print("Undone " + str(self._shape_items[last_index]))
        self._exporter.undo_last(len(self._shape_items))
        self.canvas.delete(self._shape_items[last_index])
        self._shape_items.pop(last_index)

    def on_click(self, event: tk.Event) -> None:
        """Description: On click
        Inputs: event: tk.Event
        """
        lx = event.x
        ly = event.y
        point = (self._snap(lx) - 5, self._snap(ly))
        self._points.append(point)

        shape_type = self._get_shape_type()
        color = self._get_color()

        if shape_type == "Line":
            self._handle_line(color)
        elif shape_type == "Rectangle":
            self._handle_rectangle(color)
        elif shape_type == "Box":
            self._handle_box(color)
        elif shape_type == "Circle (Filled)":
            self._handle_circle(color, fill=True)
        elif shape_type == "Circle":
            self._handle_circle(color, fill=False)

    def _snap(self, value: float) -> float:
        """Description: Snap
        Inputs: value: float
        """
        return round((value / self._snap_amount), 0) * self._snap_amount

    def _to_egp_x(self, x: float) -> float:
        """Description: To egp x
        Inputs: x: float
        """
        return ((config.CANVAS_WIDTH / 2 - x) * -1) * 2

    def _to_egp_y(self, y: float) -> float:
        """Description: To egp y
        Inputs: y: float
        """
        return (config.CANVAS_HEIGHT / 2 - y) * 2

    def _color_to_rgb(self, color: str) -> Tuple[float, float, float]:
        """Description: Color to rgb
        Inputs: color: str
        """
        rgba = colors.to_rgba(color)
        return rgba[0] * 255, rgba[1] * 255, rgba[2] * 255

    def _handle_line(self, color: str) -> None:
        """Description: Handle line
        Inputs: color: str
        """
        if len(self._points) == 1:
            print("Point 1 Placed")
            return
        if len(self._points) != 2:
            return
        print("Point 2 Placed")

        item_id = self.canvas.create_line(self._points[0], self._points[1], fill=color)
        self._shape_items.append(item_id)

        ox = self._to_egp_x(self._points[0][0])
        oy = self._to_egp_y(self._points[0][1])
        ax = self._to_egp_x(self._points[1][0])
        ay = self._to_egp_y(self._points[1][1])
        rgb = self._color_to_rgb(color)

        self._exporter.append_line(len(self._shape_items), (ox, oy * -1), (ax, ay * -1), rgb)
        self._points.clear()

    def _handle_rectangle(self, color: str) -> None:
        """Description: Handle rectangle
        Inputs: color: str
        """
        if len(self._points) == 1:
            print("Point 1 Placed")
            return
        if len(self._points) != 2:
            return
        print("Point 2 Placed")

        item_id = self.canvas.create_rectangle(self._points[0], self._points[1], outline=color)
        self._shape_items.append(item_id)

        rw = self._points[0][0] - self._points[1][0]
        rh = self._points[0][1] - self._points[1][1]
        originx = self._points[0][0] - rw / 2
        originy = self._points[0][1] - rh / 2
        ox = self._to_egp_x(originx)
        oy = self._to_egp_y(originy)
        size = (abs(rw), abs(rh))
        rgb = self._color_to_rgb(color)

        self._exporter.append_box_outline(len(self._shape_items), (ox, oy), size, rgb)
        self._points.clear()

    def _handle_box(self, color: str) -> None:
        """Description: Handle box
        Inputs: color: str
        """
        if len(self._points) == 1:
            print("Point 1 Placed")
            return
        if len(self._points) != 2:
            return
        print("Point 2 Placed")

        item_id = self.canvas.create_rectangle(self._points[0], self._points[1], fill=color)
        self._shape_items.append(item_id)

        rw = self._points[0][0] - self._points[1][0]
        rh = self._points[0][1] - self._points[1][1]
        originx = self._points[0][0] - rw / 2
        originy = self._points[0][1] - rh / 2
        ox = self._to_egp_x(originx)
        oy = self._to_egp_y(originy)
        size = (abs(rw), abs(rh))
        rgb = self._color_to_rgb(color)

        self._exporter.append_box(len(self._shape_items), (ox, oy), size, rgb)
        self._points.clear()

    def _handle_circle(self, color: str, fill: bool) -> None:
        """Description: Handle circle
        Inputs: color: str, fill: bool
        """
        if len(self._points) == 1:
            print("Point 1 Placed")
            return
        if len(self._points) != 2:
            return
        print("Point 2 Placed")

        if fill:
            item_id = self.canvas.create_oval(self._points[0], self._points[1], fill=color, outline=color)
        else:
            item_id = self.canvas.create_oval(self._points[0], self._points[1], outline=color)
        self._shape_items.append(item_id)

        rw = self._points[0][0] - self._points[1][0]
        rh = self._points[0][1] - self._points[1][1]
        originx = self._points[0][0] - rw / 2
        originy = self._points[0][1] - rh / 2
        ox = self._to_egp_x(originx)
        oy = self._to_egp_y(originy)
        size = (abs(rw), abs(rh))
        rgb = self._color_to_rgb(color)

        self._exporter.append_circle(len(self._shape_items), (ox, oy), size, rgb)
        self._points.clear()

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple
import math

import tkinter as tk
import tkinter.font as tkfont

import config
from model import Project, Shape


Point = Tuple[float, float]


class CanvasView:
    def __init__(
        self,
        master: tk.Widget,
        project: Project,
        on_selection_changed=None,
        on_project_changed=None,
        on_view_changed=None,
        on_shape_created=None,
    ) -> None:
        """Description: Init
        Inputs: master: tk.Widget, project: Project, on_selection_changed, on_project_changed, on_view_changed, on_shape_created
        """
        self.project = project
        self.canvas = tk.Canvas(master, bg=config.THEME["bg"], highlightthickness=0)

        self.tool = "select"
        self.settings = {
            "stroke": config.DEFAULT_STROKE,
            "stroke_width": config.DEFAULT_STROKE_WIDTH,
            "fill": config.DEFAULT_FILL,
            "text": config.DEFAULT_TEXT,
            "font": config.DEFAULT_FONT,
            "font_size": config.DEFAULT_FONT_SIZE,
            "align": "left",
        }

        self.active_layer_id = project.active_layer_id

        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.auto_fit = True

        self.grid_minor = config.GRID_MINOR_STEP
        self.grid_major = config.GRID_MAJOR_STEP

        self._shape_items: Dict[str, List[int]] = {}
        self._item_to_shape: Dict[int, str] = {}
        self._selected_shape_ids: Set[str] = set()
        self._on_selection_changed = on_selection_changed
        self._on_project_changed = on_project_changed
        self._on_view_changed = on_view_changed
        self._on_shape_created = on_shape_created

        self._drag_start: Optional[Point] = None
        self._drag_start_screen: Optional[Point] = None
        self._temp_item: Optional[int] = None
        self._selection_box: Optional[int] = None
        self._poly_points: List[Point] = []
        self._drag_vertex: Optional[Tuple[str, int]] = None
        self._drag_vertex_start: Optional[Point] = None
        self._scale_drag: Optional[dict] = None
        self._move_drag: Optional[dict] = None
        self._clipboard: List[Dict] = []

        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<ButtonPress-1>", self._on_left_press)
        self.canvas.bind("<B1-Motion>", self._on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_release)
        self.canvas.bind("<Double-Button-1>", self._on_left_double)
        self.canvas.bind("<ButtonPress-3>", self._on_right_press)
        self.canvas.bind("<B3-Motion>", self._on_right_drag)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<KeyPress-Escape>", self._on_escape)
        self.canvas.bind("<KeyPress-Return>", self._on_enter)
        self.canvas.bind("<ButtonPress-2>", self._on_middle_press)
        self.canvas.bind("<B2-Motion>", self._on_middle_drag)
        self.canvas.focus_set()

    @property
    def selected_shape_ids(self) -> Set[str]:
        """Description: Selected shape ids
        Inputs: None
        """
        return set(self._selected_shape_ids)

    def set_project(self, project: Project, fit_view: bool = True, redraw: bool = True) -> None:
        """Description: Set project
        Inputs: project: Project, fit_view: bool, redraw: bool
        """
        self.project = project
        self.active_layer_id = project.active_layer_id
        self._selected_shape_ids.clear()
        if fit_view:
            self.auto_fit = True
            self.fit_to_view()
        else:
            self.auto_fit = False
        if redraw:
            self.draw()

    def set_tool(self, tool: str) -> None:
        """Description: Set tool
        Inputs: tool: str
        """
        self.tool = tool
        self._clear_temp()

    def set_active_layer(self, layer_id: str) -> None:
        """Description: Set active layer
        Inputs: layer_id: str
        """
        self.active_layer_id = layer_id
        # Keep interaction scoped to the active layer.
        active = self.project.get_layer(layer_id)
        if not active:
            self.set_selected_shapes(set())
            return
        active_ids = {shape.id for shape in active.shapes}
        filtered = {sid for sid in self._selected_shape_ids if sid in active_ids}
        if filtered != self._selected_shape_ids:
            self.set_selected_shapes(filtered)

    def set_grid(self, minor: int, major: int) -> None:
        """Description: Set grid
        Inputs: minor: int, major: int
        """
        self.grid_minor = max(5, int(minor))
        self.grid_major = max(self.grid_minor, int(major))
        self.draw()

    def update_settings(self, updates: Dict[str, object]) -> None:
        """Description: Update settings
        Inputs: updates: Dict[str, object]
        """
        self.settings.update(updates)

    def apply_settings_to_selected(self, keys: Optional[List[str]] = None) -> None:
        """Description: Apply settings to selected
        Inputs: keys: Optional[List[str]]
        """
        if not self._selected_shape_ids:
            return
        key_set = set(keys) if keys else None
        for shape in self._iter_shapes():
            if shape.id not in self._selected_shape_ids:
                continue
            if key_set is None or "stroke" in key_set:
                shape.stroke = str(self.settings["stroke"])
            if key_set is None or "stroke_width" in key_set:
                if shape.kind in ("circle", "circle_filled"):
                    shape.stroke_width = 1
                else:
                    shape.stroke_width = int(self.settings["stroke_width"])
            if key_set is None or "fill" in key_set:
                shape.fill = str(self.settings["fill"]) if self.settings.get("fill") else None
            if key_set is None or "text" in key_set:
                shape.text = str(self.settings["text"])
            if key_set is None or "font" in key_set:
                shape.font = str(self.settings["font"])
            if key_set is None or "font_size" in key_set:
                shape.font_size = int(self.settings["font_size"])
            if key_set is None or "align" in key_set:
                shape.align = str(self.settings.get("align", "left"))
        self.draw()
        self._notify_project_changed()

    def set_selected_shapes(self, shape_ids: Set[str]) -> None:
        """Description: Set selected shapes
        Inputs: shape_ids: Set[str]
        """
        self._selected_shape_ids = set(shape_ids)
        self._update_selection_highlight()
        if self._on_selection_changed:
            shapes = [self._find_shape(shape_id) for shape_id in self._selected_shape_ids]
            self._on_selection_changed([shape for shape in shapes if shape is not None])

    def move_selected_to_center_offset(self, offset: Point) -> None:
        """Description: Move selected to center offset
        Inputs: offset: Point
        """
        if not self._selected_shape_ids:
            return
        res_w, res_h = self.project.resolution
        target_world = (offset[0] + res_w / 2, offset[1] + res_h / 2)
        current = self._selection_center()
        if current is None:
            return
        dx = target_world[0] - current[0]
        dy = target_world[1] - current[1]
        for shape_id in list(self._selected_shape_ids):
            shape = self._find_shape(shape_id)
            if not shape:
                continue
            shape.points = [(p[0] + dx, p[1] + dy) for p in shape.points]
        self.draw()
        self._notify_project_changed()

    def selection_center_offset(self) -> Optional[Point]:
        """Description: Selection center offset
        Inputs: None
        """
        center = self._selection_center()
        if center is None:
            return None
        res_w, res_h = self.project.resolution
        return (center[0] - res_w / 2, center[1] - res_h / 2)

    def fit_to_view(self) -> None:
        """Description: Fit to view
        Inputs: None
        """
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        res_w, res_h = self.project.resolution
        self.zoom = min(width / res_w, height / res_h)
        self.pan_x = (width - res_w * self.zoom) / 2
        self.pan_y = (height - res_h * self.zoom) / 2
        self.auto_fit = True
        self._notify_view_changed()

    def zoom_in(self) -> None:
        """Description: Zoom in
        Inputs: None
        """
        self._zoom_at_center(config.ZOOM_STEP)

    def zoom_out(self) -> None:
        """Description: Zoom out
        Inputs: None
        """
        self._zoom_at_center(1 / config.ZOOM_STEP)

    def draw(self) -> None:
        """Description: Draw
        Inputs: None
        """
        self.canvas.delete("grid")
        self.canvas.delete("shape")
        self.canvas.delete("selection")
        self._shape_items.clear()
        self._item_to_shape.clear()

        self._draw_grid()
        for layer in self.project.layers:
            if not layer.visible:
                continue
            for shape in layer.shapes:
                item_ids = self._draw_shape(shape)
                if item_ids:
                    self._shape_items[shape.id] = item_ids
                    for item_id in item_ids:
                        self._item_to_shape[item_id] = shape.id
        self._update_selection_highlight()
        self._notify_selection_changed_live()

    def _notify_selection_changed_live(self) -> None:
        """Description: Notify selection changed live
        Inputs: None
        """
        if not self._on_selection_changed:
            return
        shapes = [self._find_shape(shape_id) for shape_id in self._selected_shape_ids]
        self._on_selection_changed([shape for shape in shapes if shape is not None])

    def _draw_grid(self) -> None:
        """Description: Draw grid
        Inputs: None
        """
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 0 or height <= 0:
            return
        base_major = max(2, int(self.grid_major))
        steps: List[Tuple[int, str]] = []
        if base_major % 8 == 0:
            steps.append((base_major // 8, config.THEME["grid"]))
        if base_major % 4 == 0:
            steps.append((base_major // 4, config.THEME["grid_super"]))
        if base_major % 2 == 0:
            steps.append((base_major // 2, config.THEME["grid_major"]))
        steps.append((base_major, config.THEME["grid_base"]))
        top_left = self.screen_to_world((0, 0))
        bottom_right = self.screen_to_world((width, height))
        res_w, res_h = self.project.resolution
        min_x = max(0, int(math.floor(top_left[0])))
        min_y = max(0, int(math.floor(top_left[1])))
        max_x = min(res_w, int(math.ceil(bottom_right[0])))
        max_y = min(res_h, int(math.ceil(bottom_right[1])))

        center_x = res_w / 2
        center_y = res_h / 2
        def start_for(step: int) -> Tuple[int, int]:
            """Description: Start for
            Inputs: step: int
            """
            sx = center_x + (math.floor((min_x - center_x) / step) * step)
            sy = center_y + (math.floor((min_y - center_y) / step) * step)
            return int(sx), int(sy)

        # Draw from finest to coarsest; only include divisors of base_major.
        for step, color in steps:
            sx, sy = start_for(step)
            for x in range(sx, max_x + 1, step):
                p1 = self.world_to_screen((x, min_y))
                p2 = self.world_to_screen((x, max_y))
                self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=color, width=1, tags="grid")
            for y in range(sy, max_y + 1, step):
                p1 = self.world_to_screen((min_x, y))
                p2 = self.world_to_screen((max_x, y))
                self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=color, width=1, tags="grid")

        tl = self.world_to_screen((0, 0))
        br = self.world_to_screen((res_w, res_h))
        self.canvas.create_rectangle(tl[0], tl[1], br[0], br[1], outline=config.THEME["grid_super"], width=1, tags="grid")
        center = self.world_to_screen((res_w / 2, res_h / 2))
        self.canvas.create_line(tl[0], center[1], br[0], center[1], fill=config.THEME["grid_center"], width=2, tags="grid")
        self.canvas.create_line(center[0], tl[1], center[0], br[1], fill=config.THEME["grid_center"], width=2, tags="grid")

    def _draw_shape(self, shape: Shape) -> List[int]:
        """Description: Draw shape
        Inputs: shape: Shape
        """
        if not shape.points:
            return []
        item_ids: List[int] = []
        stroke_width = max(1, int(shape.stroke_width))
        layer_color = self._layer_color_for_shape(shape)
        stroke = layer_color or shape.stroke
        fill = shape.fill
        if fill is None and layer_color and shape.kind not in ("box", "circle_filled", "poly"):
            fill = layer_color

        if shape.kind == "line" and len(shape.points) >= 2:
            p1 = self.world_to_screen(shape.points[0])
            p2 = self.world_to_screen(shape.points[1])
            item_ids.append(
                self.canvas.create_line(
                    p1[0], p1[1], p2[0], p2[1],
                    fill=stroke,
                    width=stroke_width,
                    tags="shape",
                )
            )
        elif shape.kind in ("rect", "box") and len(shape.points) >= 2:
            p1 = self.world_to_screen(shape.points[0])
            p2 = self.world_to_screen(shape.points[1])
            if shape.kind == "box":
                outline = fill or stroke
                fill_color = fill or stroke
            else:
                outline = stroke
                fill_color = ""
            item_ids.append(
                self.canvas.create_rectangle(
                    p1[0], p1[1], p2[0], p2[1],
                    outline=outline,
                    width=stroke_width,
                    fill=fill_color,
                    tags="shape",
                )
            )
        elif shape.kind in ("circle", "circle_filled") and len(shape.points) >= 2:
            p1 = self.world_to_screen(shape.points[0])
            p2 = self.world_to_screen(shape.points[1])
            if shape.kind == "circle_filled":
                outline = fill or stroke
                fill_color = fill or stroke
            else:
                outline = stroke
                fill_color = ""
            # Editor rule: circles are always displayed with thickness 1.
            item_ids.append(
                self.canvas.create_oval(
                    p1[0], p1[1], p2[0], p2[1],
                    outline=outline,
                    width=1,
                    fill=fill_color,
                    tags="shape",
                )
            )
        elif shape.kind == "poly" and len(shape.points) >= 3:
            pts = []
            for point in shape.points:
                sp = self.world_to_screen(point)
                pts.extend([sp[0], sp[1]])
            fill_color = fill or stroke
            item_ids.append(
                self.canvas.create_polygon(
                    pts,
                    outline=fill_color,
                    width=stroke_width,
                    fill=fill_color,
                    tags="shape",
                )
            )
        elif shape.kind == "text":
            p = self.world_to_screen(shape.points[0])
            size = max(1, int(shape.font_size * 0.5 * self.zoom))
            anchor = "w" if shape.align == "left" else "center" if shape.align == "center" else "e"
            font = (shape.font or config.DEFAULT_FONT, size)
            item_ids.append(
                self.canvas.create_text(
                    p[0], p[1],
                    text=shape.text,
                    fill=stroke,
                    anchor=anchor,
                    font=font,
                    tags="shape",
                )
            )
        return item_ids

    def world_to_screen(self, point: Point) -> Point:
        """Description: World to screen
        Inputs: point: Point
        """
        return (point[0] * self.zoom + self.pan_x, point[1] * self.zoom + self.pan_y)

    def screen_to_world(self, point: Point) -> Point:
        """Description: Screen to world
        Inputs: point: Point
        """
        return ((point[0] - self.pan_x) / self.zoom, (point[1] - self.pan_y) / self.zoom)

    def _on_resize(self, _event: tk.Event) -> None:
        """Description: On resize
        Inputs: _event: tk.Event
        """
        if self.auto_fit:
            self.fit_to_view()
        self.draw()

    def _on_left_press(self, event: tk.Event) -> None:
        """Description: On left press
        Inputs: event: tk.Event
        """
        self.canvas.focus_set()
        if self.tool == "select":
            # For lines, vertex drag should win over box-scale handles so endpoints
            # resize from one side instead of scaling both ends around center.
            selected_line_only = False
            if len(self._selected_shape_ids) == 1:
                sid = next(iter(self._selected_shape_ids))
                s = self._find_shape(sid)
                selected_line_only = bool(s and s.kind == "line")

            if selected_line_only:
                vertex = self._find_vertex_at(event)
                if vertex:
                    self._drag_vertex = vertex
                    shape = self._find_shape(vertex[0])
                    if shape and len(shape.points) > vertex[1]:
                        self._drag_vertex_start = shape.points[vertex[1]]
                    return

            handle = self._find_scale_handle_at(event)
            if handle:
                self._begin_scale_drag(handle, event)
                return
            vertex = self._find_vertex_at(event)
            if vertex:
                self._drag_vertex = vertex
                shape = self._find_shape(vertex[0])
                if shape and len(shape.points) > vertex[1]:
                    self._drag_vertex_start = shape.points[vertex[1]]
                return
            if self._hit_selection_bounds(event):
                self._begin_move_drag(event)
                return
            hit = self._select_at(event)
            if not hit:
                self._drag_start = (event.x, event.y)
                self._drag_start_screen = (event.x, event.y)
            return

        if self._active_layer_locked():
            return

        world = self._snap_if_ctrl(self.screen_to_world((event.x, event.y)), event)
        self._drag_start = world
        self._drag_start_screen = (event.x, event.y)
        if self.tool in ("line", "rect", "box", "circle", "circle_filled"):
            self._temp_item = self._create_temp_shape(world, world)
        elif self.tool == "poly":
            self._poly_points.append(world)
            self._update_poly_preview()
        elif self.tool == "text":
            self._create_text_shape(world)

    def _on_left_drag(self, event: tk.Event) -> None:
        """Description: On left drag
        Inputs: event: tk.Event
        """
        if self.tool == "select":
            if self._move_drag:
                self._update_move_drag(event)
                return
            if self._scale_drag:
                self._update_scale_drag(event)
                return
            if self._drag_vertex:
                self._drag_vertex_to(event)
                return
            if not self._drag_start:
                return
            self._update_selection_box(event)
            return
        if self.tool not in ("line", "rect", "box", "circle", "circle_filled"):
            return
        if not self._drag_start or self._temp_item is None:
            return
        world = self._snap_if_ctrl(self.screen_to_world((event.x, event.y)), event)
        if self.tool in ("circle", "circle_filled") and self._ctrl_down(event):
            dx = world[0] - self._drag_start[0]
            dy = world[1] - self._drag_start[1]
            p1 = (self._drag_start[0] - dx, self._drag_start[1] - dy)
            p2 = (self._drag_start[0] + dx, self._drag_start[1] + dy)
            self._update_temp_shape(p1, p2)
        else:
            self._update_temp_shape(self._drag_start, world)

    def _on_left_release(self, event: tk.Event) -> None:
        """Description: On left release
        Inputs: event: tk.Event
        """
        if self.tool == "select":
            if self._move_drag:
                self._end_move_drag()
                return
            if self._scale_drag:
                self._end_scale_drag()
                return
            if self._drag_vertex:
                self._drag_vertex = None
                self._drag_vertex_start = None
                self._notify_project_changed()
                return
            if self._drag_start:
                self._finalize_selection_box(event)
            return
        if self.tool not in ("line", "rect", "box", "circle", "circle_filled"):
            return
        if not self._drag_start:
            return
        world = self._snap_if_ctrl(self.screen_to_world((event.x, event.y)), event)
        if self.tool in ("circle", "circle_filled") and self._ctrl_down(event):
            dx = world[0] - self._drag_start[0]
            dy = world[1] - self._drag_start[1]
            p1 = (self._drag_start[0] - dx, self._drag_start[1] - dy)
            p2 = (self._drag_start[0] + dx, self._drag_start[1] + dy)
            self._finalize_drag_shape(p1, p2)
        else:
            self._finalize_drag_shape(self._drag_start, world)
        self._drag_start = None
        self._drag_start_screen = None

    def _on_left_double(self, _event: tk.Event) -> None:
        """Description: On left double
        Inputs: _event: tk.Event
        """
        if self.tool == "poly":
            self._finish_poly()

    def _on_escape(self, _event: tk.Event) -> None:
        """Description: On escape
        Inputs: _event: tk.Event
        """
        self._clear_temp()

    def _on_enter(self, _event: tk.Event) -> None:
        """Description: On enter
        Inputs: _event: tk.Event
        """
        if self.tool == "poly":
            self._finish_poly()

    def _on_right_press(self, event: tk.Event) -> None:
        """Description: On right press
        Inputs: event: tk.Event
        """
        self._drag_start = (event.x, event.y)

    def _on_right_drag(self, event: tk.Event) -> None:
        """Description: On right drag
        Inputs: event: tk.Event
        """
        if self._drag_start is None:
            return
        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        self.pan_x += dx
        self.pan_y += dy
        self._drag_start = (event.x, event.y)
        self.auto_fit = False
        self.draw()
        self._notify_view_changed()

    def _on_middle_press(self, event: tk.Event) -> None:
        """Description: On middle press
        Inputs: event: tk.Event
        """
        self._drag_start = (event.x, event.y)

    def _on_middle_drag(self, event: tk.Event) -> None:
        """Description: On middle drag
        Inputs: event: tk.Event
        """
        self._on_right_drag(event)

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        """Description: On mouse wheel
        Inputs: event: tk.Event
        """
        factor = config.ZOOM_STEP if event.delta > 0 else 1 / config.ZOOM_STEP
        self._zoom_at(event.x, event.y, factor)

    def _zoom_at_center(self, factor: float) -> None:
        """Description: Zoom at center
        Inputs: factor: float
        """
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        self._zoom_at(width / 2, height / 2, factor)

    def _zoom_at(self, x: float, y: float, factor: float) -> None:
        """Description: Zoom at
        Inputs: x: float, y: float, factor: float
        """
        old_zoom = self.zoom
        new_zoom = min(config.ZOOM_MAX, max(config.ZOOM_MIN, self.zoom * factor))
        if new_zoom == old_zoom:
            return
        world = self.screen_to_world((x, y))
        self.zoom = new_zoom
        self.pan_x = x - world[0] * self.zoom
        self.pan_y = y - world[1] * self.zoom
        self.auto_fit = False
        self.draw()
        self._notify_view_changed()

    def _select_at(self, event: tk.Event) -> bool:
        """Description: Select at
        Inputs: event: tk.Event
        """
        hit = self.canvas.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2)
        if not hit:
            self.set_selected_shapes(set())
            return False

        active_layer = self.project.get_layer(self.active_layer_id)
        active_ids = {shape.id for shape in active_layer.shapes} if active_layer else set()

        shape_id = None
        for item_id in hit:
            if item_id not in self._item_to_shape:
                continue
            sid = self._item_to_shape[item_id]
            if sid in active_ids:
                shape_id = sid
                break
        if shape_id:
            if event.state & 0x0001:
                selected = set(self._selected_shape_ids)
                if shape_id in selected:
                    selected.remove(shape_id)
                else:
                    selected.add(shape_id)
                self.set_selected_shapes(selected)
            else:
                self.set_selected_shapes({shape_id})
            return True
        self.set_selected_shapes(set())
        return False

    def _update_selection_highlight(self) -> None:
        """Description: Update selection highlight
        Inputs: None
        """
        self.canvas.delete("selection")
        if not self._selected_shape_ids:
            return
        bounds = self._selection_bounds()
        if not bounds:
            return
        p1 = self.world_to_screen(bounds[0])
        p2 = self.world_to_screen(bounds[1])
        if self.tool != "select":
            self.canvas.create_rectangle(
                p1[0], p1[1], p2[0], p2[1],
                outline=config.THEME["grid_major"],
                width=1,
                tags="selection",
            )
            return
        self.canvas.create_rectangle(
            p1[0], p1[1], p2[0], p2[1],
            outline=config.THEME["accent_alt"],
            dash=(4, 2),
            tags="selection",
        )
        self._draw_vertex_handles()
        self._draw_scale_handles(p1, p2)

    def _shape_bounds(self, shape: Shape) -> Optional[Tuple[Point, Point]]:
        """Description: Shape bounds
        Inputs: shape: Shape
        """
        if shape.kind == "text":
            if not shape.points:
                return None
            x, y = shape.points[0]
            display_size = max(1, int(shape.font_size * 0.5 * self.zoom))
            try:
                font = tkfont.Font(family=shape.font or config.DEFAULT_FONT, size=display_size)
                text_width = max(font.measure(shape.text or " "), 1)
                text_height = max(font.metrics("linespace"), 1)
            except Exception:
                text_width = max(int(display_size * max(len(shape.text), 1) * 0.6), 1)
                text_height = max(display_size, 1)
            half_w = (text_width / self.zoom) / 2
            half_h = (text_height / self.zoom) / 2
            if shape.align == "center":
                left = x - half_w
                right = x + half_w
            elif shape.align == "right":
                left = x - (text_width / self.zoom)
                right = x
            else:
                left = x
                right = x + (text_width / self.zoom)
            top = y - half_h
            bottom = y + half_h
            pad = 1 / max(self.zoom, 0.001)
            return (left - pad, top - pad), (right + pad, bottom + pad)
        if not shape.points:
            return None
        xs = [p[0] for p in shape.points]
        ys = [p[1] for p in shape.points]
        return (min(xs), min(ys)), (max(xs), max(ys))

    def _create_temp_shape(self, start: Point, end: Point) -> Optional[int]:
        """Description: Create temp shape
        Inputs: start: Point, end: Point
        """
        if self.tool == "line":
            p1 = self.world_to_screen(start)
            p2 = self.world_to_screen(end)
            return self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=self.settings["stroke"], dash=(4, 2), tags="shape")
        if self.tool in ("rect", "box"):
            p1 = self.world_to_screen(start)
            p2 = self.world_to_screen(end)
            return self.canvas.create_rectangle(p1[0], p1[1], p2[0], p2[1], outline=self.settings["stroke"], dash=(4, 2), tags="shape")
        if self.tool in ("circle", "circle_filled"):
            p1 = self.world_to_screen(start)
            p2 = self.world_to_screen(end)
            return self.canvas.create_oval(p1[0], p1[1], p2[0], p2[1], outline=self.settings["stroke"], dash=(4, 2), tags="shape")
        return None

    def _update_temp_shape(self, start: Point, end: Point) -> None:
        """Description: Update temp shape
        Inputs: start: Point, end: Point
        """
        if self._temp_item is None:
            return
        p1 = self.world_to_screen(start)
        p2 = self.world_to_screen(end)
        self.canvas.coords(self._temp_item, p1[0], p1[1], p2[0], p2[1])

    def _finalize_drag_shape(self, start: Point, end: Point) -> None:
        """Description: Finalize drag shape
        Inputs: start: Point, end: Point
        """
        if self._active_layer_locked():
            self._clear_temp()
            return
        if self._temp_item is not None:
            self.canvas.delete(self._temp_item)
            self._temp_item = None
        if start == end:
            return
        shape = self._shape_from_drag(start, end)
        if shape is None:
            return
        layer = self.project.get_layer(self.active_layer_id)
        if not layer:
            return
        layer.shapes.append(shape)
        if self._on_shape_created:
            self._on_shape_created(shape)
        self.draw()
        self._notify_project_changed()

    def _shape_from_drag(self, start: Point, end: Point) -> Optional[Shape]:
        """Description: Shape from drag
        Inputs: start: Point, end: Point
        """
        shape_id = self.project.new_shape_id()
        stroke = str(self.settings["stroke"])
        stroke_width = int(self.settings["stroke_width"])
        fill = str(self.settings["fill"]) if self.settings.get("fill") else None
        if self.tool == "line":
            return Shape(id=shape_id, kind="line", points=[start, end], stroke=stroke, stroke_width=stroke_width)
        if self.tool == "rect":
            return Shape(id=shape_id, kind="rect", points=[start, end], stroke=stroke, stroke_width=stroke_width)
        if self.tool == "box":
            return Shape(id=shape_id, kind="box", points=[start, end], stroke=stroke, stroke_width=stroke_width, fill=fill)
        if self.tool == "circle":
            return Shape(id=shape_id, kind="circle", points=[start, end], stroke=stroke, stroke_width=1)
        if self.tool == "circle_filled":
            return Shape(id=shape_id, kind="circle_filled", points=[start, end], stroke=stroke, stroke_width=1, fill=fill)
        return None

    def _create_text_shape(self, point: Point) -> None:
        """Description: Create text shape
        Inputs: point: Point
        """
        if self._active_layer_locked():
            return
        text = self._prompt_text(self.settings["text"])
        if text is None:
            return
        shape = Shape(
            id=self.project.new_shape_id(),
            kind="text",
            points=[point],
            stroke=str(self.settings["stroke"]),
            stroke_width=int(self.settings["stroke_width"]),
            text=str(text),
            font=str(self.settings["font"]),
            font_size=int(self.settings["font_size"]),
            align=str(self.settings.get("align", "left")),
        )
        layer = self.project.get_layer(self.active_layer_id)
        if not layer:
            return
        layer.shapes.append(shape)
        if self._on_shape_created:
            self._on_shape_created(shape)
        self.draw()
        self._notify_project_changed()

    def _update_poly_preview(self) -> None:
        """Description: Update poly preview
        Inputs: None
        """
        if self._temp_item is not None:
            self.canvas.delete(self._temp_item)
        if len(self._poly_points) < 2:
            return
        points = []
        for point in self._poly_points:
            sp = self.world_to_screen(point)
            points.extend([sp[0], sp[1]])
        self._temp_item = self.canvas.create_line(*points, fill=self.settings["stroke"], dash=(4, 2), tags="shape")

    def _finish_poly(self) -> None:
        """Description: Finish poly
        Inputs: None
        """
        if len(self._poly_points) < 3:
            self._clear_temp()
            return
        shape = Shape(
            id=self.project.new_shape_id(),
            kind="poly",
            points=list(self._poly_points),
            stroke=str(self.settings["stroke"]),
            stroke_width=int(self.settings["stroke_width"]),
            fill=str(self.settings["fill"]) if self.settings.get("fill") else None,
        )
        layer = self.project.get_layer(self.active_layer_id)
        if not layer:
            return
        layer.shapes.append(shape)
        if self._on_shape_created:
            self._on_shape_created(shape)
        self._clear_temp()
        self.draw()
        self._notify_project_changed()

    def _notify_project_changed(self) -> None:
        """Description: Notify project changed
        Inputs: None
        """
        if self._on_project_changed:
            self._on_project_changed()

    def _notify_view_changed(self) -> None:
        """Description: Notify view changed
        Inputs: None
        """
        if self._on_view_changed:
            self._on_view_changed()

    def finish_poly(self) -> None:
        """Description: Finish poly
        Inputs: None
        """
        if self.tool == "poly":
            self._finish_poly()

    def _clear_temp(self) -> None:
        """Description: Clear temp
        Inputs: None
        """
        if self._temp_item is not None:
            self.canvas.delete(self._temp_item)
        self._temp_item = None
        self._poly_points.clear()
        if self._selection_box is not None:
            self.canvas.delete(self._selection_box)
        self._selection_box = None

    def _find_shape(self, shape_id: str) -> Optional[Shape]:
        """Description: Find shape
        Inputs: shape_id: str
        """
        for layer in self.project.layers:
            for shape in layer.shapes:
                if shape.id == shape_id:
                    return shape
        return None

    def _layer_color_for_shape(self, shape: Shape) -> Optional[str]:
        """Description: Layer color for shape
        Inputs: shape: Shape
        """
        for layer in self.project.layers:
            if shape in layer.shapes:
                return layer.color
        return None

    def _active_layer_locked(self) -> bool:
        """Description: Active layer locked
        Inputs: None
        """
        layer = self.project.get_layer(self.active_layer_id)
        return bool(layer and layer.locked)

    def _update_selection_box(self, event: tk.Event) -> None:
        """Description: Update selection box
        Inputs: event: tk.Event
        """
        if not self._drag_start:
            return
        if self._selection_box is None:
            self._selection_box = self.canvas.create_rectangle(
                self._drag_start[0], self._drag_start[1], event.x, event.y,
                outline=config.THEME["accent"], dash=(4, 2), tags="selection",
            )
        else:
            self.canvas.coords(self._selection_box, self._drag_start[0], self._drag_start[1], event.x, event.y)

    def _finalize_selection_box(self, event: tk.Event) -> None:
        """Description: Finalize selection box
        Inputs: event: tk.Event
        """
        if not self._drag_start:
            return
        start = self._drag_start
        end = (event.x, event.y)
        if self._drag_start_screen:
            if abs(end[0] - self._drag_start_screen[0]) < 4 and abs(end[1] - self._drag_start_screen[1]) < 4:
                self.set_selected_shapes(set())
                self._selection_box = None
                self._drag_start = None
                self._drag_start_screen = None
                return
        if self._selection_box is not None:
            self.canvas.delete(self._selection_box)
        self._selection_box = None
        self._drag_start = None
        self._drag_start_screen = None
        if start == end:
            return
        world_start = self.screen_to_world(start)
        world_end = self.screen_to_world(end)
        min_x = min(world_start[0], world_end[0])
        max_x = max(world_start[0], world_end[0])
        min_y = min(world_start[1], world_end[1])
        max_y = max(world_start[1], world_end[1])
        selected: Set[str] = set()
        layer = self.project.get_layer(self.active_layer_id)
        if layer and layer.visible:
            for shape in layer.shapes:
                bounds = self._shape_bounds(shape)
                if not bounds:
                    continue
                b1, b2 = bounds
                if b2[0] < min_x or b1[0] > max_x or b2[1] < min_y or b1[1] > max_y:
                    continue
                selected.add(shape.id)
        self.set_selected_shapes(selected)

    def delete_selected(self) -> None:
        """Description: Delete selected
        Inputs: None
        """
        if not self._selected_shape_ids:
            return
        for layer in self.project.layers:
            layer.shapes = [shape for shape in layer.shapes if shape.id not in self._selected_shape_ids]
        self.set_selected_shapes(set())
        self.draw()
        self._notify_project_changed()

    def copy_selected(self) -> None:
        """Description: Copy selected
        Inputs: None
        """
        if not self._selected_shape_ids:
            return
        payloads: List[Dict] = []
        for layer in self.project.layers:
            for shape in layer.shapes:
                if shape.id in self._selected_shape_ids:
                    payloads.append(shape.to_dict())
        self._clipboard = payloads

    def paste_clipboard(self, offset: Point = (10, 10)) -> None:
        """Description: Paste clipboard
        Inputs: offset: Point
        """
        if not self._clipboard:
            return
        if self._active_layer_locked():
            return
        layer = self.project.get_layer(self.active_layer_id)
        if not layer:
            return
        new_ids: Set[str] = set()
        dx, dy = offset
        for payload in self._clipboard:
            shape = Shape.from_dict(payload)
            shape.id = self.project.new_shape_id()
            if shape.points:
                shape.points = [(p[0] + dx, p[1] + dy) for p in shape.points]
            layer.shapes.append(shape)
            new_ids.add(shape.id)
        if new_ids:
            self.set_selected_shapes(new_ids)
        self.draw()
        self._notify_project_changed()

    def mirror_selected(self, axis: str, copy: bool = True) -> None:
        """Description: Mirror selected
        Inputs: axis: str, copy: bool
        """
        if not self._selected_shape_ids:
            return
        res_w, res_h = self.project.resolution
        new_ids: Set[str] = set()
        for layer in self.project.layers:
            new_shapes: List[Shape] = []
            for shape in layer.shapes:
                if shape.id not in self._selected_shape_ids:
                    continue
                target = shape
                if copy:
                    target = Shape.from_dict(shape.to_dict())
                    target.id = self.project.new_shape_id()
                    new_ids.add(target.id)
                mirrored = []
                for x, y in target.points:
                    if axis == "x":
                        mirrored.append((res_w - x, y))
                    elif axis == "y":
                        mirrored.append((x, res_h - y))
                    else:
                        mirrored.append((x, y))
                target.points = mirrored
                if copy:
                    new_shapes.append(target)
            if copy and new_shapes:
                layer.shapes.extend(new_shapes)
        if copy:
            self.set_selected_shapes(new_ids)
        self.draw()
        self._notify_project_changed()

    def _ctrl_down(self, event: tk.Event) -> bool:
        """Description: Ctrl down
        Inputs: event: tk.Event
        """
        return bool(event.state & 0x0004)

    def _snap_if_ctrl(self, world: Point, event: tk.Event) -> Point:
        """Description: Snap if ctrl
        Inputs: world: Point, event: tk.Event
        """
        if not self._ctrl_down(event):
            return world
        base_major = max(2, int(self.grid_major))
        steps = []
        if base_major % 8 == 0:
            steps.append(base_major // 8)
        if base_major % 4 == 0:
            steps.append(base_major // 4)
        if base_major % 2 == 0:
            steps.append(base_major // 2)
        steps.append(base_major)
        step = min(steps)
        if step <= 0:
            return world
        center_x = self.project.resolution[0] / 2
        center_y = self.project.resolution[1] / 2
        snap_x = center_x + round((world[0] - center_x) / step) * step
        snap_y = center_y + round((world[1] - center_y) / step) * step
        snapped = (snap_x, snap_y)

        # Keep circle Ctrl-resize predictable: grid snap only, no text-guide magnetism.
        if self.tool in ("circle", "circle_filled"):
            return snapped

        return self._snap_to_text_edges(snapped)

    def _snap_to_text_edges(self, world: Point) -> Point:
        """Description: Snap to text edges
        Inputs: world: Point
        """
        threshold = 6 / max(self.zoom, 0.001)
        target_x = world[0]
        target_y = world[1]
        best_dx = threshold
        best_dy = threshold
        for layer in self.project.layers:
            if not layer.visible:
                continue
            for shape in layer.shapes:
                if shape.kind != "text":
                    continue
                bounds = self._shape_bounds(shape)
                if not bounds:
                    continue
                (x1, y1), (x2, y2) = bounds

                # Snap to perceived text guides: left/right + visual center.
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2

                for guide_x in (x1, center_x, x2):
                    dx = abs(world[0] - guide_x)
                    if dx <= best_dx:
                        best_dx = dx
                        target_x = guide_x
                for guide_y in (y1, center_y, y2):
                    dy = abs(world[1] - guide_y)
                    if dy <= best_dy:
                        best_dy = dy
                        target_y = guide_y
        return (target_x, target_y)

    def _shift_down(self, event: tk.Event) -> bool:
        """Description: Shift down
        Inputs: event: tk.Event
        """
        return bool(event.state & 0x0001)

    def _find_vertex_at(self, event: tk.Event) -> Optional[Tuple[str, int]]:
        """Description: Find vertex at
        Inputs: event: tk.Event
        """
        world = self.screen_to_world((event.x, event.y))
        threshold = 12 / max(self.zoom, 0.001)
        selected = self._selected_shape_ids
        active_layer = self.project.get_layer(self.active_layer_id)
        if not active_layer or not active_layer.visible:
            return None

        for shape in active_layer.shapes:
                if selected and shape.id not in selected:
                    continue
                points = shape.points
                if not points:
                    continue
                if shape.kind not in ("poly", "line", "rect", "box", "circle", "circle_filled", "text"):
                    continue
                for idx, point in enumerate(points):
                    dx = point[0] - world[0]
                    dy = point[1] - world[1]
                    if (dx * dx + dy * dy) ** 0.5 <= threshold:
                        self.set_selected_shapes({shape.id})
                        return (shape.id, idx)
        return None

    def _drag_vertex_to(self, event: tk.Event) -> None:
        """Description: Drag vertex to
        Inputs: event: tk.Event
        """
        if not self._drag_vertex:
            return
        shape = self._find_shape(self._drag_vertex[0])
        if not shape:
            return
        world = self._snap_if_ctrl(self.screen_to_world((event.x, event.y)), event)
        if self._drag_vertex_start and self._shift_down(event):
            dx = abs(world[0] - self._drag_vertex_start[0])
            dy = abs(world[1] - self._drag_vertex_start[1])
            if dx >= dy:
                world = (world[0], self._drag_vertex_start[1])
            else:
                world = (self._drag_vertex_start[0], world[1])
        shape.points[self._drag_vertex[1]] = world
        self.draw()

    def _selection_center(self) -> Optional[Point]:
        """Description: Selection center
        Inputs: None
        """
        if not self._selected_shape_ids:
            return None
        xs: List[float] = []
        ys: List[float] = []
        for shape_id in self._selected_shape_ids:
            shape = self._find_shape(shape_id)
            if not shape:
                continue
            for point in shape.points:
                xs.append(point[0])
                ys.append(point[1])
        if not xs or not ys:
            return None
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def _prompt_text(self, initial: str) -> Optional[str]:
        """Description: Prompt text
        Inputs: initial: str
        """
        try:
            import tkinter.simpledialog as simpledialog
        except Exception:
            return None
        return simpledialog.askstring("Text", "Enter text:", initialvalue=str(initial))

    def _selection_bounds(self) -> Optional[Tuple[Point, Point]]:
        """Description: Selection bounds
        Inputs: None
        """
        if not self._selected_shape_ids:
            return None
        xs: List[float] = []
        ys: List[float] = []
        for shape_id in self._selected_shape_ids:
            shape = self._find_shape(shape_id)
            if not shape:
                continue
            bounds = self._shape_bounds(shape)
            if not bounds:
                continue
            (x1, y1), (x2, y2) = bounds
            xs.extend([x1, x2])
            ys.extend([y1, y2])
        if not xs or not ys:
            return None
        return (min(xs), min(ys)), (max(xs), max(ys))

    def _draw_vertex_handles(self) -> None:
        """Description: Draw vertex handles
        Inputs: None
        """
        size = 4
        for shape_id in self._selected_shape_ids:
            shape = self._find_shape(shape_id)
            if not shape or not shape.points:
                continue
            for point in shape.points:
                sp = self.world_to_screen(point)
                self.canvas.create_rectangle(
                    sp[0] - size, sp[1] - size, sp[0] + size, sp[1] + size,
                    outline=config.THEME["accent"],
                    fill=config.THEME["panel_alt"],
                    tags="selection",
                )

    def _draw_scale_handles(self, p1: Point, p2: Point) -> None:
        """Description: Draw scale handles
        Inputs: p1: Point, p2: Point
        """
        size = 6
        corners = [
            (p1[0], p1[1]),
            (p2[0], p1[1]),
            (p2[0], p2[1]),
            (p1[0], p2[1]),
        ]
        for x, y in corners:
            self.canvas.create_rectangle(
                x - size, y - size, x + size, y + size,
                outline=config.THEME["accent_alt"],
                fill=config.THEME["panel_alt"],
                tags="selection",
            )

    def _find_scale_handle_at(self, event: tk.Event) -> Optional[str]:
        """Description: Find scale handle at
        Inputs: event: tk.Event
        """
        bounds = self._selection_bounds()
        if not bounds:
            return None
        p1 = self.world_to_screen(bounds[0])
        p2 = self.world_to_screen(bounds[1])
        handles = {
            "tl": (p1[0], p1[1]),
            "tr": (p2[0], p1[1]),
            "br": (p2[0], p2[1]),
            "bl": (p1[0], p2[1]),
        }
        size = 8
        for key, (x, y) in handles.items():
            if abs(event.x - x) <= size and abs(event.y - y) <= size:
                return key
        return None

    def _begin_scale_drag(self, handle: str, event: tk.Event) -> None:
        """Description: Begin scale drag
        Inputs: handle: str, event: tk.Event
        """
        bounds = self._selection_bounds()
        if not bounds:
            return
        center = self._selection_center()
        if not center:
            return
        points: Dict[str, List[Point]] = {}
        for shape in self._iter_shapes():
            if shape.id in self._selected_shape_ids:
                points[shape.id] = list(shape.points)
        self._scale_drag = {
            "handle": handle,
            "start": (event.x, event.y),
            "center": center,
            "bounds": bounds,
            "points": points,
        }

    def _update_scale_drag(self, event: tk.Event) -> None:
        """Description: Update scale drag
        Inputs: event: tk.Event
        """
        if not self._scale_drag:
            return
        center = self._scale_drag["center"]
        (min_x, min_y), (max_x, max_y) = self._scale_drag["bounds"]
        handle = self._scale_drag["handle"]
        world = self.screen_to_world((event.x, event.y))
        if handle in ("tl", "bl"):
            old_x = min_x
        else:
            old_x = max_x
        if handle in ("tl", "tr"):
            old_y = min_y
        else:
            old_y = max_y
        old_dx = max(abs(old_x - center[0]), 1e-6)
        old_dy = max(abs(old_y - center[1]), 1e-6)
        new_dx = max(abs(world[0] - center[0]), 1e-6)
        new_dy = max(abs(world[1] - center[1]), 1e-6)
        sx = new_dx / old_dx
        sy = new_dy / old_dy
        for shape_id, points in self._scale_drag["points"].items():
            shape = self._find_shape(shape_id)
            if not shape:
                continue
            shape.points = [((p[0] - center[0]) * sx + center[0], (p[1] - center[1]) * sy + center[1]) for p in points]
        self.draw()

    def _end_scale_drag(self) -> None:
        """Description: End scale drag
        Inputs: None
        """
        if not self._scale_drag:
            return
        self._scale_drag = None
        self._notify_project_changed()

    def _hit_selection_bounds(self, event: tk.Event) -> bool:
        """Description: Hit selection bounds
        Inputs: event: tk.Event
        """
        bounds = self._selection_bounds()
        if not bounds:
            return False
        world = self.screen_to_world((event.x, event.y))
        (x1, y1), (x2, y2) = bounds

        tol = 6 / max(self.zoom, 0.001)
        # Works for thin selections (e.g., horizontal/vertical lines) too.
        if (x1 - tol) <= world[0] <= (x2 + tol) and (y1 - tol) <= world[1] <= (y2 + tol):
            return True

        # For a single selected line, allow drag when cursor is near the segment.
        if len(self._selected_shape_ids) == 1:
            sid = next(iter(self._selected_shape_ids))
            shape = self._find_shape(sid)
            if shape and shape.kind == "line" and len(shape.points) >= 2:
                (ax, ay), (bx, by) = shape.points[0], shape.points[1]
                vx = bx - ax
                vy = by - ay
                wx = world[0] - ax
                wy = world[1] - ay
                seg_len2 = vx * vx + vy * vy
                if seg_len2 <= 1e-9:
                    dist2 = wx * wx + wy * wy
                else:
                    t = max(0.0, min(1.0, (wx * vx + wy * vy) / seg_len2))
                    px = ax + t * vx
                    py = ay + t * vy
                    dx = world[0] - px
                    dy = world[1] - py
                    dist2 = dx * dx + dy * dy
                if dist2 <= tol * tol:
                    return True

        return False

    def _begin_move_drag(self, event: tk.Event) -> None:
        """Description: Begin move drag
        Inputs: event: tk.Event
        """
        if not self._selected_shape_ids:
            return
        start = self.screen_to_world((event.x, event.y))
        points: Dict[str, List[Point]] = {}
        for shape in self._iter_shapes():
            if shape.id in self._selected_shape_ids:
                points[shape.id] = list(shape.points)
        self._move_drag = {
            "start": start,
            "points": points,
        }

    def _update_move_drag(self, event: tk.Event) -> None:
        """Description: Update move drag
        Inputs: event: tk.Event
        """
        if not self._move_drag:
            return
        start = self._move_drag["start"]
        world = self._snap_if_ctrl(self.screen_to_world((event.x, event.y)), event)
        dx = world[0] - start[0]
        dy = world[1] - start[1]
        if self._shift_down(event):
            if abs(dx) >= abs(dy):
                dy = 0
            else:
                dx = 0
        for shape_id, points in self._move_drag["points"].items():
            shape = self._find_shape(shape_id)
            if not shape:
                continue
            shape.points = [(p[0] + dx, p[1] + dy) for p in points]
        self.draw()

    def _end_move_drag(self) -> None:
        """Description: End move drag
        Inputs: None
        """
        if not self._move_drag:
            return
        self._move_drag = None
        self._notify_project_changed()

    def _iter_shapes(self) -> List[Shape]:
        """Description: Iter shapes
        Inputs: None
        """
        shapes: List[Shape] = []
        for layer in self.project.layers:
            shapes.extend(layer.shapes)
        return shapes

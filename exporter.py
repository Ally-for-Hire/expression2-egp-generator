# HUD export to Expression2 EGP.

from __future__ import annotations

from typing import Dict, Iterable, Tuple
import re

from model import Project, Shape


class HudExporter:
    def __init__(self, path: str) -> None:
        """Description: Init
        Inputs: path: str
        """
        self.path = path
        self._header_lines: list[str] = []

    def export(self, project: Project) -> None:
        """Description: Export
        Inputs: project: Project
        """
        self._header_lines = self._build_header(project)
        with open(self.path, "w", encoding="utf-8") as file:
            file.writelines(self._header_lines)

        egp_id = 0
        dynamic_text: Dict[int, str] = {}
        for layer in project.layers:
            if not layer.visible:
                continue
            for shape in layer.shapes:
                egp_id += 1
                text_expr, is_dynamic = self._text_expression(project, shape)
                self._export_shape(egp_id, project.resolution, layer.color, shape, text_expr)
                if is_dynamic:
                    dynamic_text[egp_id] = text_expr

        self._write_lines(["}\n\n"])
        if dynamic_text:
            self._write_lines(self._build_dynamic_block(dynamic_text))

    def _build_header(self, project: Project) -> list[str]:
        """Description: Build header
        Inputs: project: Project
        """
        inputs = ["EGP:wirelink"]
        for input_def in project.inputs:
            if not input_def.name:
                continue
            input_type = "normal" if input_def.type.lower() == "normal" else "string"
            inputs.append(f"{input_def.name}:{input_type}")
        inputs_line = "@inputs " + " ".join(inputs) + "\n"
        resolution = project.resolution
        return [
            "@name Untitled\n",
            inputs_line,
            "@persist X Y Res:vector2 ProjRes:vector2 Scale:vector2\n\n",
            "if ( first() )\n",
            "{\n",
            "    EGP:egpClear()\n",
            "    Res = egpScrSize(owner())\n",
            "    X   = Res:x()\n",
            "    Y   = Res:y()\n",
            "    Res /= 2\n",
            f"    ProjRes = vec2( {resolution[0]}, {resolution[1]} )\n",
            "    Scale = vec2(X/ProjRes:x(), Y/ProjRes:y())\n",
            "    interval(100)\n",
        ]

    def _write_lines(self, lines: Iterable[str]) -> None:
        """Description: Write lines
        Inputs: lines: Iterable[str]
        """
        with open(self.path, "a", encoding="utf-8") as file:
            file.writelines(lines)

    def _fmt_num(self, value: float) -> str:
        """Description: Format numeric output with 1 decimal place
        Inputs: value: float
        """
        rounded = round(float(value), 1)
        if abs(rounded) < 0.05:
            rounded = 0.0
        return f"{rounded:.1f}"

    def _offset_expr(self, resolution: Tuple[int, int], point: Tuple[float, float]) -> str:
        """Description: Offset expr
        Inputs: resolution: Tuple[int, int], point: Tuple[float, float]
        """
        dx = point[0] - resolution[0] / 2
        dy = point[1] - resolution[1] / 2
        return f"Res+vec2( {self._fmt_num(dx)}*Scale:x(), {self._fmt_num(dy)}*Scale:y())"

    def _size_expr(self, value: float) -> str:
        """Description: Size expr
        Inputs: value: float
        """
        v = self._fmt_num(value)
        return f"vec2( {v}*Scale:x(), {v}*Scale:x())"

    def _size_xy_expr(self, width: float, height: float) -> str:
        """Description: Size xy expr
        Inputs: width: float, height: float
        """
        return f"vec2( {self._fmt_num(width)}*Scale:x(), {self._fmt_num(height)}*Scale:y())"

    def _color_vec(self, color: str) -> Tuple[int, int, int]:
        """Description: Color vec
        Inputs: color: str
        """
        color = color.lstrip("#")
        if len(color) != 6:
            return (255, 255, 255)
        return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))

    def _alpha_value(self, shape: Shape) -> int:
        """Description: Alpha value
        Inputs: shape: Shape
        """
        return max(0, min(255, int(getattr(shape, "alpha", 255))))

    def _export_shape(self, egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape, text_expr: str | None) -> None:
        """Description: Export shape
        Inputs: egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape, text_expr: str | None
        """
        if shape.kind == "line":
            self._export_line(egp_id, resolution, layer_color, shape)
        elif shape.kind == "rect":
            self._export_rect(egp_id, resolution, layer_color, shape)
        elif shape.kind == "box":
            self._export_box(egp_id, resolution, layer_color, shape)
        elif shape.kind == "circle":
            self._export_circle(egp_id, resolution, layer_color, shape, filled=False)
        elif shape.kind == "circle_filled":
            self._export_circle(egp_id, resolution, layer_color, shape, filled=True)
        elif shape.kind == "poly":
            self._export_poly(egp_id, resolution, layer_color, shape)
        elif shape.kind == "text":
            self._export_text(egp_id, resolution, layer_color, shape, text_expr)

    def _export_line(self, egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape) -> None:
        """Description: Export line
        Inputs: egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape
        """
        if len(shape.points) < 2:
            return
        (x1, y1), (x2, y2) = shape.points[0], shape.points[1]
        rgb = self._color_vec(layer_color or shape.stroke)
        stroke = max(1, int(shape.stroke_width))
        # Loose axis-aligned detection: if the delta rounds down to 0 at whole-pixel
        # precision, treat it as axis-aligned and export as a box for cleaner thickness.
        dy_rounded = round(abs(y2 - y1), 0)
        dx_rounded = round(abs(x2 - x1), 0)
        horizontalish = dy_rounded == 0
        verticalish = dx_rounded == 0

        if horizontalish or verticalish:
            if horizontalish:
                width = max(abs(x2 - x1), 1)
                height = stroke
            else:
                width = stroke
                height = max(abs(y2 - y1), 1)
            cx, cy, _, _ = self._bounds_center((x1, y1), (x2, y2))
            center = self._offset_expr(resolution, (cx, cy))
            lines = [
                f"    EGP:egpBox( {egp_id}, {center}, {self._size_xy_expr(width, height)} )\n",
                f"    EGP:egpColor( {egp_id},vec({rgb[0]}, {rgb[1]}, {rgb[2]}))\n",
                f"    EGP:egpAlpha( {egp_id}, {self._alpha_value(shape)} )\n",
            ]
            self._write_lines(lines)
            return
        p1 = self._offset_expr(resolution, (x1, y1))
        p2 = self._offset_expr(resolution, (x2, y2))
        lines = [
            f"    EGP:egpLine( {egp_id}, {p1}, {p2} )\n",
            f"    EGP:egpColor( {egp_id},vec({rgb[0]}, {rgb[1]}, {rgb[2]}))\n",
            f"    EGP:egpAlpha( {egp_id}, {self._alpha_value(shape)} )\n",
        ]
        self._write_lines(lines)

    def _export_rect(self, egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape) -> None:
        """Description: Export rect
        Inputs: egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape
        """
        if len(shape.points) < 2:
            return
        cx, cy, w, h = self._bounds_center(shape.points[0], shape.points[1])
        center = self._offset_expr(resolution, (cx, cy))
        rgb = self._color_vec(layer_color or shape.stroke)
        lines = [
            f"    EGP:egpBoxOutline( {egp_id}, {center}, {self._size_xy_expr(w, h)} )\n",
            f"    EGP:egpColor( {egp_id},vec({rgb[0]}, {rgb[1]}, {rgb[2]}))\n",
            f"    EGP:egpAlpha( {egp_id}, {self._alpha_value(shape)} )\n",
        ]
        self._write_lines(lines)

    def _export_box(self, egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape) -> None:
        """Description: Export box
        Inputs: egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape
        """
        if len(shape.points) < 2:
            return
        cx, cy, w, h = self._bounds_center(shape.points[0], shape.points[1])
        center = self._offset_expr(resolution, (cx, cy))
        rgb = self._color_vec(layer_color or shape.fill or shape.stroke)
        lines = [
            f"    EGP:egpBox( {egp_id}, {center}, {self._size_xy_expr(w, h)} )\n",
            f"    EGP:egpColor( {egp_id},vec({rgb[0]}, {rgb[1]}, {rgb[2]}))\n",
            f"    EGP:egpAlpha( {egp_id}, {self._alpha_value(shape)} )\n",
        ]
        self._write_lines(lines)

    def _export_circle(self, egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape, filled: bool = False) -> None:
        """Description: Export circle
        Inputs: egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape, filled: bool = False
        """
        if len(shape.points) < 2:
            return
        cx, cy, w, h = self._bounds_center(shape.points[0], shape.points[1])
        center = self._offset_expr(resolution, (cx, cy))
        color = layer_color or shape.fill or shape.stroke
        rgb = self._color_vec(color)
        circle_call = "egpCircle" if filled else "egpCircleOutline"
        lines = [
            f"    EGP:{circle_call}( {egp_id}, {center}, {self._size_xy_expr(w/2, h/2)} )\n",
            f"    EGP:egpColor( {egp_id},vec({rgb[0]}, {rgb[1]}, {rgb[2]}))\n",
            f"    EGP:egpAlpha( {egp_id}, {self._alpha_value(shape)} )\n",
        ]
        self._write_lines(lines)

    def _export_poly(self, egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape) -> None:
        """Description: Export poly
        Inputs: egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape
        """
        if len(shape.points) < 3:
            return
        points = [self._offset_expr(resolution, point) for point in shape.points]
        poly_points = ",".join(points)
        rgb = self._color_vec(layer_color or shape.fill or shape.stroke)
        lines = [
            f"    EGP:egpPoly( {egp_id},array( {poly_points} ))\n",
            f"    EGP:egpColor( {egp_id},vec({rgb[0]}, {rgb[1]}, {rgb[2]}))\n",
            f"    EGP:egpAlpha( {egp_id}, {self._alpha_value(shape)} )\n",
        ]
        self._write_lines(lines)

    def _export_text(self, egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape, text_expr: str | None) -> None:
        """Description: Export text
        Inputs: egp_id: int, resolution: Tuple[int, int], layer_color: str | None, shape: Shape, text_expr: str | None
        """
        if not shape.points:
            return
        point = self._offset_expr(resolution, shape.points[0])
        text = text_expr or self._quote_text(shape.text)
        rgb = self._color_vec(layer_color or shape.stroke)
        align_h = 0
        if shape.align == "center":
            align_h = 1
        elif shape.align == "right":
            align_h = 2
        align_v = 1
        lines = [
            f"    EGP:egpText( {egp_id}, {text}, {point} )\n",
            f"    EGP:egpColor( {egp_id},vec({rgb[0]}, {rgb[1]}, {rgb[2]}))\n",
            f"    EGP:egpAlpha( {egp_id}, {self._alpha_value(shape)} )\n",
            f"    EGP:egpAlign( {egp_id}, {align_h}, {align_v} )\n",
        ]
        if shape.font:
            lines.append(f"    EGP:egpFont( {egp_id},\"{shape.font}\", {shape.font_size} )\n")
        else:
            lines.append(f"    EGP:egpFont( {egp_id},\"Default\", {shape.font_size} )\n")
        self._write_lines(lines)

    def _bounds_center(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> Tuple[float, float, float, float]:
        """Description: Bounds center
        Inputs: p1: Tuple[float, float], p2: Tuple[float, float]
        """
        min_x = min(p1[0], p2[0])
        max_x = max(p1[0], p2[0])
        min_y = min(p1[1], p2[1])
        max_y = max(p1[1], p2[1])
        w = max_x - min_x
        h = max_y - min_y
        cx = min_x + w / 2
        cy = min_y + h / 2
        return cx, cy, w, h

    def _quote_text(self, text: str) -> str:
        """Description: Quote text
        Inputs: text: str
        """
        escaped = text.replace("\\", "\\\\").replace("\"", "\\\"")
        return f"\"{escaped}\""

    def _text_expression(self, project: Project, shape: Shape) -> Tuple[str, bool]:
        """Description: Text expression
        Inputs: project: Project, shape: Shape
        """
        if shape.kind != "text":
            return self._quote_text(shape.text), False
        token_re = re.compile(r"%([A-Za-z0-9_]+)%(R(\d))?")
        inputs = {input_def.name: input_def.type for input_def in project.inputs}
        parts: list[str] = []
        last = 0
        is_dynamic = False
        matches = list(token_re.finditer(shape.text))

        for match in matches:
            name = match.group(1)
            rounding = match.group(3)
            if name not in inputs:
                continue
            is_dynamic = True
            if match.start() > last:
                parts.append(self._quote_text(shape.text[last:match.start()]))
            value_expr = name
            if inputs[name].lower() == "normal" and rounding:
                value_expr = f"round({name},{rounding})"
            parts.append(value_expr)
            last = match.end()

        if not is_dynamic:
            return self._quote_text(shape.text), False

        if last < len(shape.text):
            parts.append(self._quote_text(shape.text[last:]))

        expr = " + ".join(parts) if parts else self._quote_text(shape.text)

        # E2 egpText expects a string; when the text is only a single numeric token
        # (e.g. "%Speed%" or "%Speed%R0"), force string coercion.
        if len(matches) == 1:
            m = matches[0]
            name = m.group(1)
            covers_full_text = (m.start() == 0 and m.end() == len(shape.text))
            if covers_full_text and name in inputs and inputs[name].lower() == "normal":
                expr = f"({expr}) + \"\""

        return expr, True

    def _build_dynamic_block(self, dynamic_text: Dict[int, str]) -> list[str]:
        """Description: Build dynamic block
        Inputs: dynamic_text: Dict[int, str]
        """
        lines = ["if (clk())\n", "{\n", "   interval(100)\n"]
        for egp_id, expr in dynamic_text.items():
            lines.append(f"   EGP:egpSetText( {egp_id}, {expr} )\n")
        lines.append("}\n")
        return lines

from __future__ import annotations

import tkinter as tk
import os
import tempfile
from tkinter import filedialog, messagebox, simpledialog, colorchooser

import config
from canvas_view import CanvasView
from exporter import HudExporter
from model import InputDef, Project, Shape
from storage import load_project, save_project


class EgpApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(config.WINDOW_TITLE)
        self.root.configure(bg=config.THEME["bg"])
        self.root.geometry("1400x900")

        self.project = Project.new(config.DEFAULT_RESOLUTION)
        self.project_path: str | None = None
        self.is_dirty = False

        self._suppress_property_update = False
        self._center_x_var = tk.StringVar()
        self._center_y_var = tk.StringVar()
        self._history: list[dict] = []
        self._restoring = False

        self._build_menu()
        self._build_layout()
        self._bind_shortcuts()

        self._set_tool("select")
        self.canvas_view.fit_to_view()
        self.canvas_view.draw()
        self._refresh_layers()
        self._update_status()
        self._push_undo_state()

    def run(self) -> None:
        self.root.mainloop()

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)

        file_menu = tk.Menu(menu, tearoff=0)
        file_menu.add_command(label="New", command=self.new_project)
        file_menu.add_command(label="Open...", command=self.open_project)
        file_menu.add_command(label="Save", command=self.save_project)
        file_menu.add_command(label="Save As...", command=self.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export HUD...", command=self.export_hud)
        file_menu.add_command(label="Copy HUD to Clipboard", command=self.copy_hud_to_clipboard)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menu.add_cascade(label="File", menu=file_menu)

        view_menu = tk.Menu(menu, tearoff=0)
        view_menu.add_command(label="Zoom In", command=self.zoom_in)
        view_menu.add_command(label="Zoom Out", command=self.zoom_out)
        view_menu.add_command(label="Fit to View", command=self._fit_to_view)
        menu.add_cascade(label="View", menu=view_menu)

        layer_menu = tk.Menu(menu, tearoff=0)
        layer_menu.add_command(label="New Layer", command=self.add_layer)
        layer_menu.add_command(label="Duplicate Layer", command=self.duplicate_layer)
        layer_menu.add_command(label="Delete Layer", command=self.delete_layer)
        layer_menu.add_command(label="Move Layer Up", command=lambda: self.move_layer(-1))
        layer_menu.add_command(label="Move Layer Down", command=lambda: self.move_layer(1))
        menu.add_cascade(label="Layer", menu=layer_menu)

        help_menu = tk.Menu(menu, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menu.add_cascade(label="Help", menu=help_menu)

    def _build_layout(self) -> None:
        self.main_frame = tk.Frame(self.root, bg=config.THEME["bg"])
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.main_frame.columnconfigure(0, weight=0)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.columnconfigure(2, weight=0)
        self.main_frame.rowconfigure(0, weight=1)

        self.toolbar_frame = tk.Frame(self.main_frame, bg=config.THEME["panel"], padx=10, pady=10)
        self.toolbar_frame.grid(row=0, column=0, sticky="ns")

        self.canvas_frame = tk.Frame(self.main_frame, bg=config.THEME["bg"], padx=8, pady=8)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew")
        self.canvas_frame.rowconfigure(0, weight=1)
        self.canvas_frame.columnconfigure(0, weight=1)

        self.sidebar_frame = tk.Frame(self.main_frame, bg=config.THEME["panel"], padx=10, pady=10)
        self.sidebar_frame.grid(row=0, column=2, sticky="ns")
        self.sidebar_frame.rowconfigure(0, weight=0)
        self.sidebar_frame.rowconfigure(1, weight=1)

        self.canvas_view = CanvasView(
            self.canvas_frame,
            self.project,
            on_selection_changed=self._on_selection_changed,
            on_project_changed=self._mark_dirty,
            on_view_changed=self._update_status,
            on_shape_created=self._on_shape_created,
        )
        self.canvas_view.canvas.grid(row=0, column=0, sticky="nsew")

        self._build_toolbar()
        self._build_properties_panel()
        self._build_layers_panel()
        self._build_status_bar()

    def _build_toolbar(self) -> None:
        header = tk.Label(self.toolbar_frame, text="Tools", bg=config.THEME["panel"], fg=config.THEME["text"], font=("Segoe UI", 12, "bold"))
        header.pack(anchor="w", pady=(0, 10))

        self.tool_buttons: dict[str, tk.Button] = {}
        tool_specs = [
            ("Select", "select"),
            ("Line", "line"),
            ("Rect", "rect"),
            ("Box", "box"),
            ("Circle", "circle"),
            ("Circle+", "circle_filled"),
            ("Poly", "poly"),
            ("Text", "text"),
        ]
        for label, tool in tool_specs:
            button = tk.Button(
                self.toolbar_frame,
                text=label,
                command=lambda t=tool: self._set_tool(t),
                bg=config.THEME["panel_alt"],
                fg=config.THEME["text"],
                activebackground=config.THEME["accent"],
                activeforeground=config.THEME["text"],
                relief=tk.FLAT,
                width=10,
                pady=4,
            )
            button.pack(fill=tk.X, pady=4)
            self.tool_buttons[tool] = button

        sep = tk.Frame(self.toolbar_frame, bg=config.THEME["panel_alt"], height=2)
        sep.pack(fill=tk.X, pady=8)

        finish_poly = tk.Button(
            self.toolbar_frame,
            text="Finish Poly",
            command=self.canvas_view.finish_poly,
            bg=config.THEME["panel_alt"],
            fg=config.THEME["text"],
            relief=tk.FLAT,
            pady=4,
        )
        finish_poly.pack(fill=tk.X, pady=4)

        delete_btn = tk.Button(
            self.toolbar_frame,
            text="Delete",
            command=self.canvas_view.delete_selected,
            bg=config.THEME["panel_alt"],
            fg=config.THEME["text"],
            relief=tk.FLAT,
            pady=4,
        )
        delete_btn.pack(fill=tk.X, pady=4)

        mirror_x = tk.Button(
            self.toolbar_frame,
            text="Mirror X",
            command=lambda: self.canvas_view.mirror_selected("x", copy=True),
            bg=config.THEME["panel_alt"],
            fg=config.THEME["text"],
            relief=tk.FLAT,
            pady=4,
        )
        mirror_x.pack(fill=tk.X, pady=4)

        mirror_y = tk.Button(
            self.toolbar_frame,
            text="Mirror Y",
            command=lambda: self.canvas_view.mirror_selected("y", copy=True),
            bg=config.THEME["panel_alt"],
            fg=config.THEME["text"],
            relief=tk.FLAT,
            pady=4,
        )
        mirror_y.pack(fill=tk.X, pady=4)

        zoom_in = tk.Button(
            self.toolbar_frame,
            text="Zoom +",
            command=self.zoom_in,
            bg=config.THEME["panel_alt"],
            fg=config.THEME["text"],
            relief=tk.FLAT,
            pady=4,
        )
        zoom_in.pack(fill=tk.X, pady=4)

        zoom_out = tk.Button(
            self.toolbar_frame,
            text="Zoom -",
            command=self.zoom_out,
            bg=config.THEME["panel_alt"],
            fg=config.THEME["text"],
            relief=tk.FLAT,
            pady=4,
        )
        zoom_out.pack(fill=tk.X, pady=4)

        fit = tk.Button(
            self.toolbar_frame,
            text="Fit",
            command=self._fit_to_view,
            bg=config.THEME["panel_alt"],
            fg=config.THEME["text"],
            relief=tk.FLAT,
            pady=4,
        )
        fit.pack(fill=tk.X, pady=4)

    def _build_properties_panel(self) -> None:
        self.properties_frame = tk.Frame(self.sidebar_frame, bg=config.THEME["panel"])
        self.properties_frame.grid(row=0, column=0, sticky="new")

        title = tk.Label(self.properties_frame, text="Properties", bg=config.THEME["panel"], fg=config.THEME["text"], font=("Segoe UI", 12, "bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="w")

        self.editing_label = tk.Label(self.properties_frame, text="Editing: Tool Defaults", bg=config.THEME["panel"], fg=config.THEME["muted"], font=("Segoe UI", 10))
        self.editing_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.stroke_var = tk.StringVar(value=config.DEFAULT_STROKE)
        self.fill_var = tk.StringVar(value=config.DEFAULT_FILL)
        self.stroke_width_var = tk.IntVar(value=config.DEFAULT_STROKE_WIDTH)
        self.text_var = tk.StringVar(value=config.DEFAULT_TEXT)
        self.font_var = tk.StringVar(value=config.DEFAULT_FONT)
        self.font_size_var = tk.IntVar(value=config.DEFAULT_FONT_SIZE)
        self.align_var = tk.StringVar(value="left")

        row = 2
        row = self._add_labeled_entry("Stroke", self.stroke_var, row)
        row = self._add_labeled_entry("Fill", self.fill_var, row)
        row = self._add_labeled_spin("Stroke Width", self.stroke_width_var, row, 1, 24)
        row = self._add_labeled_entry("Text", self.text_var, row)
        row = self._add_labeled_option("Font", self.font_var, config.FONTS, row)
        row = self._add_labeled_spin("Font Size", self.font_size_var, row, 6, 128)
        row = self._add_labeled_option("Align", self.align_var, ["left", "center", "right"], row)

        coord_label = tk.Label(self.properties_frame, text="Selection Center (X,Y)", bg=config.THEME["panel"], fg=config.THEME["muted"], font=("Segoe UI", 10))
        coord_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 2))
        row += 1

        self.center_x_entry = tk.Entry(self.properties_frame, textvariable=self._center_x_var, bg=config.THEME["panel_alt"], fg=config.THEME["text"], insertbackground=config.THEME["text"], relief=tk.FLAT)
        self.center_x_entry.grid(row=row, column=0, sticky="ew", pady=2, padx=(0, 4))
        self.center_y_entry = tk.Entry(self.properties_frame, textvariable=self._center_y_var, bg=config.THEME["panel_alt"], fg=config.THEME["text"], insertbackground=config.THEME["text"], relief=tk.FLAT)
        self.center_y_entry.grid(row=row, column=1, sticky="ew", pady=2)
        row += 1

        set_center_btn = tk.Button(
            self.properties_frame,
            text="Set Center",
            command=self._apply_center_offset,
            bg=config.THEME["panel_alt"],
            fg=config.THEME["text"],
            relief=tk.FLAT,
            pady=4,
        )
        set_center_btn.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 4))
        row += 1

        palette_label = tk.Label(self.properties_frame, text="Palette", bg=config.THEME["panel"], fg=config.THEME["muted"], font=("Segoe UI", 10))
        palette_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 4))
        row += 1

        palette_frame = tk.Frame(self.properties_frame, bg=config.THEME["panel"])
        palette_frame.grid(row=row, column=0, columnspan=2, sticky="w")
        for color in config.COLORS:
            btn = tk.Button(
                palette_frame,
                bg=color,
                width=2,
                height=1,
                relief=tk.FLAT,
                command=lambda c=color: self._apply_palette_color(c),
            )
            btn.pack(side=tk.LEFT, padx=2, pady=2)
        row += 1

        apply_button = tk.Button(
            self.properties_frame,
            text="Apply to Selection",
            command=self._apply_properties_to_selection,
            bg=config.THEME["accent"],
            fg=config.THEME["text"],
            relief=tk.FLAT,
            pady=4,
        )
        apply_button.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 4))

        self.properties_frame.columnconfigure(0, weight=1)
        self.properties_frame.columnconfigure(1, weight=1)

        self.stroke_var.trace_add("write", lambda *_: self._sync_tool_settings("stroke"))
        self.fill_var.trace_add("write", lambda *_: self._sync_tool_settings("fill"))
        self.stroke_width_var.trace_add("write", lambda *_: self._sync_tool_settings("stroke_width"))
        self.text_var.trace_add("write", lambda *_: self._sync_tool_settings("text"))
        self.font_var.trace_add("write", lambda *_: self._sync_tool_settings("font"))
        self.font_size_var.trace_add("write", lambda *_: self._sync_tool_settings("font_size"))
        self.align_var.trace_add("write", lambda *_: self._sync_tool_settings("align"))

    def _build_layers_panel(self) -> None:
        self.layers_frame = tk.Frame(self.sidebar_frame, bg=config.THEME["panel"])
        self.layers_frame.grid(row=1, column=0, sticky="nsew", pady=(16, 0))
        self.layers_frame.rowconfigure(1, weight=1)
        self.layers_frame.columnconfigure(0, weight=1)

        title = tk.Label(self.layers_frame, text="Layers", bg=config.THEME["panel"], fg=config.THEME["text"], font=("Segoe UI", 12, "bold"))
        title.grid(row=0, column=0, sticky="w")

        self.layer_list = tk.Listbox(
            self.layers_frame,
            bg=config.THEME["panel_alt"],
            fg=config.THEME["text"],
            selectbackground=config.THEME["accent"],
            selectforeground=config.THEME["text"],
            highlightthickness=0,
            activestyle="none",
        )
        self.layer_list.grid(row=1, column=0, sticky="nsew", pady=(6, 6))
        self.layer_list.bind("<<ListboxSelect>>", self._on_layer_selected)

        controls = tk.Frame(self.layers_frame, bg=config.THEME["panel"])
        controls.grid(row=2, column=0, sticky="ew")
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        tk.Button(controls, text="Add", command=self.add_layer, bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT).grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        tk.Button(controls, text="Delete", command=self.delete_layer, bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT).grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        tk.Button(controls, text="Up", command=lambda: self.move_layer(-1), bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT).grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        tk.Button(controls, text="Down", command=lambda: self.move_layer(1), bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT).grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        tk.Button(controls, text="Show/Hide", command=self.toggle_layer_visibility, bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT).grid(row=2, column=0, sticky="ew", padx=2, pady=2)
        tk.Button(controls, text="Lock/Unlock", command=self.toggle_layer_lock, bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT).grid(row=2, column=1, sticky="ew", padx=2, pady=2)
        tk.Button(controls, text="Rename", command=self.rename_layer, bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT).grid(row=3, column=0, sticky="ew", padx=2, pady=2)
        tk.Button(controls, text="Duplicate", command=self.duplicate_layer, bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT).grid(row=3, column=1, sticky="ew", padx=2, pady=2)
        tk.Button(controls, text="Layer Color", command=self.set_layer_color, bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT).grid(row=4, column=0, sticky="ew", padx=2, pady=2)
        tk.Button(controls, text="Clear Layer Color", command=self.clear_layer_color, bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT).grid(row=4, column=1, sticky="ew", padx=2, pady=2)

        res_frame = tk.Frame(self.layers_frame, bg=config.THEME["panel"])
        res_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        tk.Label(res_frame, text="Resolution", bg=config.THEME["panel"], fg=config.THEME["muted"], font=("Segoe UI", 10)).pack(anchor="w")
        self.res_var = tk.StringVar(value=self._resolution_label(self.project.resolution))
        res_menu = tk.OptionMenu(res_frame, self.res_var, *[self._resolution_label(r) for r in config.RESOLUTION_PRESETS], command=self._on_resolution_change)
        res_menu.configure(bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT, highlightthickness=0, activebackground=config.THEME["accent"])
        res_menu["menu"].configure(bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT)
        res_menu.pack(fill=tk.X, pady=(4, 0))

        inputs_frame = tk.Frame(self.layers_frame, bg=config.THEME["panel"])
        inputs_frame.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        inputs_frame.columnconfigure(0, weight=1)
        tk.Label(inputs_frame, text="Inputs", bg=config.THEME["panel"], fg=config.THEME["muted"], font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        self.inputs_list = tk.Listbox(
            inputs_frame,
            height=4,
            bg=config.THEME["panel_alt"],
            fg=config.THEME["text"],
            selectbackground=config.THEME["accent"],
            selectforeground=config.THEME["text"],
            highlightthickness=0,
            activestyle="none",
        )
        self.inputs_list.grid(row=1, column=0, sticky="ew", pady=(4, 4))
        input_controls = tk.Frame(inputs_frame, bg=config.THEME["panel"])
        input_controls.grid(row=2, column=0, sticky="ew")
        tk.Button(input_controls, text="Add Input", command=self.add_input, bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        tk.Button(input_controls, text="Remove", command=self.remove_input, bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT).grid(row=0, column=1, sticky="ew")
        input_controls.columnconfigure(0, weight=1)
        input_controls.columnconfigure(1, weight=1)

    def _build_status_bar(self) -> None:
        self.status_var = tk.StringVar(value="")
        status = tk.Label(self.root, textvariable=self.status_var, bg=config.THEME["panel_alt"], fg=config.THEME["muted"], anchor="w")
        status.pack(fill=tk.X, side=tk.BOTTOM)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-s>", self._on_save_shortcut)
        self.root.bind("<Control-o>", self._on_open_shortcut)
        self.root.bind("<Control-n>", self._on_new_shortcut)
        self.root.bind("<Control-e>", self._on_export_shortcut)
        self.root.bind("<Control-0>", self._on_fit_shortcut)
        self.root.bind("<Control-z>", self._on_undo_shortcut)
        self.root.bind("<Control-c>", self._on_copy_shortcut)
        self.root.bind("<Control-v>", self._on_paste_shortcut)
        self.root.bind("<Delete>", self._on_delete_shortcut)
        self.root.bind("<BackSpace>", self._on_delete_shortcut)

    def _text_input_focused(self) -> bool:
        widget = self.root.focus_get()
        if widget is None:
            return False
        return isinstance(widget, (tk.Entry, tk.Text, tk.Spinbox))

    def _on_save_shortcut(self, _event: tk.Event) -> None:
        if self._text_input_focused():
            return
        self.save_project()

    def _on_open_shortcut(self, _event: tk.Event) -> None:
        if self._text_input_focused():
            return
        self.open_project()

    def _on_new_shortcut(self, _event: tk.Event) -> None:
        if self._text_input_focused():
            return
        self.new_project()

    def _on_export_shortcut(self, _event: tk.Event) -> None:
        if self._text_input_focused():
            return
        self.export_hud()

    def _on_fit_shortcut(self, _event: tk.Event) -> None:
        if self._text_input_focused():
            return
        self._fit_to_view()

    def _on_undo_shortcut(self, _event: tk.Event) -> None:
        if self._text_input_focused():
            return
        self.undo()

    def _on_copy_shortcut(self, _event: tk.Event) -> None:
        if self._text_input_focused():
            return
        self.canvas_view.copy_selected()

    def _on_paste_shortcut(self, _event: tk.Event) -> None:
        if self._text_input_focused():
            return
        self.canvas_view.paste_clipboard()

    def _on_delete_shortcut(self, _event: tk.Event) -> None:
        if self._text_input_focused():
            return
        self.canvas_view.delete_selected()

    def _resolution_label(self, resolution: tuple[int, int]) -> str:
        return f"{resolution[0]}x{resolution[1]}"

    def _scale_project(self, old_res: tuple[int, int], new_res: tuple[int, int]) -> None:
        if old_res == new_res:
            return
        scale_x = new_res[0] / old_res[0]
        scale_y = new_res[1] / old_res[1]
        scale_avg = (scale_x + scale_y) / 2
        for layer in self.project.layers:
            for shape in layer.shapes:
                shape.points = [(p[0] * scale_x, p[1] * scale_y) for p in shape.points]
                shape.stroke_width = max(1, int(shape.stroke_width * scale_avg))

    def _on_resolution_change(self, label: str) -> None:
        parts = label.split("x")
        if len(parts) != 2:
            return
        old_res = self.project.resolution
        new_res = (int(parts[0]), int(parts[1]))
        self._scale_project(old_res, new_res)
        self.project.resolution = new_res
        self.canvas_view.auto_fit = True
        self.canvas_view.fit_to_view()
        self.canvas_view.draw()
        self._mark_dirty()
        self._update_status()

    def _set_tool(self, tool: str) -> None:
        self.canvas_view.set_tool(tool)
        for key, button in self.tool_buttons.items():
            if key == tool:
                button.configure(bg=config.THEME["accent"], fg=config.THEME["text"])
            else:
                button.configure(bg=config.THEME["panel_alt"], fg=config.THEME["text"])

    def _fit_to_view(self) -> None:
        self.canvas_view.fit_to_view()
        self.canvas_view.draw()
        self._update_status()

    def zoom_in(self) -> None:
        self.canvas_view.zoom_in()
        self._update_status()

    def zoom_out(self) -> None:
        self.canvas_view.zoom_out()
        self._update_status()

    def _add_labeled_entry(self, label: str, variable: tk.StringVar, row: int) -> int:
        tk.Label(self.properties_frame, text=label, bg=config.THEME["panel"], fg=config.THEME["muted"], font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w")
        entry = tk.Entry(self.properties_frame, textvariable=variable, bg=config.THEME["panel_alt"], fg=config.THEME["text"], insertbackground=config.THEME["text"], relief=tk.FLAT)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        return row + 1

    def _add_labeled_spin(self, label: str, variable: tk.IntVar, row: int, min_val: int, max_val: int) -> int:
        tk.Label(self.properties_frame, text=label, bg=config.THEME["panel"], fg=config.THEME["muted"], font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w")
        spin = tk.Spinbox(
            self.properties_frame,
            from_=min_val,
            to=max_val,
            textvariable=variable,
            bg=config.THEME["panel_alt"],
            fg=config.THEME["text"],
            buttonbackground=config.THEME["panel_alt"],
            relief=tk.FLAT,
            command=self._sync_tool_settings,
        )
        spin.grid(row=row, column=1, sticky="ew", pady=2)
        spin.bind("<Return>", lambda _e: self._sync_tool_settings())
        spin.bind("<FocusOut>", lambda _e: self._sync_tool_settings())
        return row + 1

    def _add_labeled_option(self, label: str, variable: tk.StringVar, options: list[str], row: int) -> int:
        tk.Label(self.properties_frame, text=label, bg=config.THEME["panel"], fg=config.THEME["muted"], font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w")
        menu = tk.OptionMenu(self.properties_frame, variable, *options)
        menu.configure(bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT, highlightthickness=0, activebackground=config.THEME["accent"])
        menu["menu"].configure(bg=config.THEME["panel_alt"], fg=config.THEME["text"], relief=tk.FLAT)
        menu.grid(row=row, column=1, sticky="ew", pady=2)
        return row + 1

    def _apply_palette_color(self, color: str) -> None:
        if self.canvas_view.selected_shape_ids:
            self.stroke_var.set(color)
            if self.fill_var.get():
                self.fill_var.set(color)
        else:
            self.stroke_var.set(color)

    def _sync_tool_settings(self, changed_key: str | None = None) -> None:
        if self._suppress_property_update:
            return
        updates = {
            "stroke": self.stroke_var.get(),
            "fill": self.fill_var.get(),
            "stroke_width": self.stroke_width_var.get(),
            "text": self.text_var.get(),
            "font": self.font_var.get(),
            "font_size": self.font_size_var.get(),
            "align": self.align_var.get(),
        }
        if changed_key:
            self.canvas_view.update_settings({changed_key: updates[changed_key]})
        else:
            self.canvas_view.update_settings(updates)
        if self.canvas_view.selected_shape_ids:
            keys = [changed_key] if changed_key else None
            self.canvas_view.apply_settings_to_selected(keys)
            self._mark_dirty()

    def _apply_properties_to_selection(self) -> None:
        self.canvas_view.apply_settings_to_selected()
        self._mark_dirty()

    def _on_selection_changed(self, shapes: list[Shape]) -> None:
        self._suppress_property_update = True
        if not shapes:
            self.editing_label.config(text="Editing: Tool Defaults")
            self._center_x_var.set("")
            self._center_y_var.set("")
            self._suppress_property_update = False
            return
        count = len(shapes)
        self.editing_label.config(text=f"Editing: Selection ({count})")
        shape = shapes[0]
        self.stroke_var.set(shape.stroke)
        self.fill_var.set(shape.fill or "")
        self.stroke_width_var.set(shape.stroke_width)
        self.text_var.set(shape.text)
        self.font_var.set(shape.font or config.DEFAULT_FONT)
        self.font_size_var.set(shape.font_size)
        self.align_var.set(shape.align)
        center = self.canvas_view.selection_center_offset()
        if center:
            self._center_x_var.set(f"{center[0]:.1f}")
            self._center_y_var.set(f"{center[1]:.1f}")
        self._suppress_property_update = False

    def _on_shape_created(self, shape: Shape) -> None:
        self.canvas_view.set_selected_shapes({shape.id})
        self._update_status()

    def _apply_center_offset(self) -> None:
        try:
            x = float(self._center_x_var.get())
            y = float(self._center_y_var.get())
        except ValueError:
            return
        self.canvas_view.move_selected_to_center_offset((x, y))
        self._mark_dirty()

    def _refresh_layers(self) -> None:
        self.layer_list.delete(0, tk.END)
        for layer in self.project.layers:
            vis = "V" if layer.visible else "-"
            lock = "L" if layer.locked else "-"
            color = layer.color if layer.color else "--"
            label = f"[{vis}] [{lock}] [{color}] {layer.name}"
            self.layer_list.insert(tk.END, label)
        self._select_active_layer()
        self._refresh_inputs()

    def _refresh_inputs(self) -> None:
        if not hasattr(self, "inputs_list"):
            return
        self.inputs_list.delete(0, tk.END)
        for input_def in self.project.inputs:
            self.inputs_list.insert(tk.END, f"{input_def.name}:{input_def.type}")

    def _select_active_layer(self) -> None:
        for idx, layer in enumerate(self.project.layers):
            if layer.id == self.project.active_layer_id:
                self.layer_list.selection_clear(0, tk.END)
                self.layer_list.selection_set(idx)
                self.layer_list.activate(idx)
                break

    def _on_layer_selected(self, _event: tk.Event) -> None:
        selection = self.layer_list.curselection()
        if not selection:
            return
        index = selection[0]
        layer = self.project.layers[index]
        self.project.active_layer_id = layer.id
        self.canvas_view.set_active_layer(layer.id)
        self._update_status()

    def _get_selected_layer_index(self) -> int | None:
        selection = self.layer_list.curselection()
        if not selection:
            return None
        return selection[0]

    def add_layer(self) -> None:
        name = simpledialog.askstring("New Layer", "Layer name:", parent=self.root)
        if not name:
            name = f"Layer {len(self.project.layers) + 1}"
        layer = Project.new(self.project.resolution).layers[0]
        layer.name = name
        self.project.layers.append(layer)
        self.project.active_layer_id = layer.id
        self.canvas_view.set_active_layer(layer.id)
        self._refresh_layers()
        self.canvas_view.draw()
        self._mark_dirty()

    def duplicate_layer(self) -> None:
        index = self._get_selected_layer_index()
        if index is None:
            return
        src = self.project.layers[index]
        layer = Project.new(self.project.resolution).layers[0]
        layer.name = f"{src.name} Copy"
        layer.visible = src.visible
        layer.locked = src.locked
        layer.color = src.color
        layer.shapes = [Shape.from_dict(s.to_dict()) for s in src.shapes]
        self.project.layers.insert(index + 1, layer)
        self.project.active_layer_id = layer.id
        self.canvas_view.set_active_layer(layer.id)
        self._refresh_layers()
        self.canvas_view.draw()
        self._mark_dirty()

    def delete_layer(self) -> None:
        if len(self.project.layers) <= 1:
            messagebox.showinfo("Layers", "At least one layer is required.")
            return
        index = self._get_selected_layer_index()
        if index is None:
            return
        del self.project.layers[index]
        if index >= len(self.project.layers):
            index = len(self.project.layers) - 1
        self.project.active_layer_id = self.project.layers[index].id
        self.canvas_view.set_active_layer(self.project.active_layer_id)
        self._refresh_layers()
        self.canvas_view.draw()
        self._mark_dirty()

    def move_layer(self, direction: int) -> None:
        index = self._get_selected_layer_index()
        if index is None:
            return
        new_index = index + direction
        if new_index < 0 or new_index >= len(self.project.layers):
            return
        self.project.layers[index], self.project.layers[new_index] = self.project.layers[new_index], self.project.layers[index]
        self._refresh_layers()
        self.layer_list.selection_set(new_index)
        self.layer_list.activate(new_index)
        self.canvas_view.draw()
        self._mark_dirty()

    def rename_layer(self) -> None:
        index = self._get_selected_layer_index()
        if index is None:
            return
        layer = self.project.layers[index]
        name = simpledialog.askstring("Rename Layer", "Layer name:", initialvalue=layer.name, parent=self.root)
        if not name:
            return
        layer.name = name
        self._refresh_layers()
        self._mark_dirty()

    def set_layer_color(self) -> None:
        index = self._get_selected_layer_index()
        if index is None:
            return
        layer = self.project.layers[index]
        color = colorchooser.askcolor(title="Layer Color", initialcolor=layer.color or config.DEFAULT_STROKE)
        if not color or not color[1]:
            return
        layer.color = color[1]
        self._refresh_layers()
        self.canvas_view.draw()
        self._mark_dirty()

    def clear_layer_color(self) -> None:
        index = self._get_selected_layer_index()
        if index is None:
            return
        layer = self.project.layers[index]
        layer.color = None
        self._refresh_layers()
        self.canvas_view.draw()
        self._mark_dirty()

    def toggle_layer_visibility(self) -> None:
        index = self._get_selected_layer_index()
        if index is None:
            return
        layer = self.project.layers[index]
        layer.visible = not layer.visible
        self._refresh_layers()
        self.canvas_view.draw()
        self._mark_dirty()

    def toggle_layer_lock(self) -> None:
        index = self._get_selected_layer_index()
        if index is None:
            return
        layer = self.project.layers[index]
        layer.locked = not layer.locked
        self._refresh_layers()
        self._mark_dirty()

    def add_input(self) -> None:
        value = simpledialog.askstring("Add Input", "Enter input as NAME:TYPE (Normal or String):", parent=self.root)
        if not value:
            return
        parts = value.split(":")
        if len(parts) != 2:
            messagebox.showerror("Input", "Format must be NAME:TYPE.")
            return
        name = parts[0].strip()
        input_type = parts[1].strip().capitalize()
        if input_type not in ("Normal", "String"):
            messagebox.showerror("Input", "Type must be Normal or String.")
            return
        if not name:
            messagebox.showerror("Input", "Name cannot be empty.")
            return
        for existing in self.project.inputs:
            if existing.name == name:
                existing.type = input_type
                self._refresh_inputs()
                self._mark_dirty()
                return
        self.project.inputs.append(InputDef(name=name, type=input_type))
        self._refresh_inputs()
        self._mark_dirty()

    def remove_input(self) -> None:
        if not hasattr(self, "inputs_list"):
            return
        selection = self.inputs_list.curselection()
        if not selection:
            return
        index = selection[0]
        if index < 0 or index >= len(self.project.inputs):
            return
        del self.project.inputs[index]
        self._refresh_inputs()
        self._mark_dirty()

    def new_project(self) -> None:
        if not self._confirm_discard():
            return
        self.project = Project.new(config.DEFAULT_RESOLUTION)
        self.project_path = None
        self.is_dirty = False
        self.canvas_view.set_project(self.project)
        self.res_var.set(self._resolution_label(self.project.resolution))
        self._refresh_layers()
        self._update_status()
        self._history = [self.project.to_dict()]

    def open_project(self) -> None:
        if not self._confirm_discard():
            return
        path = filedialog.askopenfilename(
            title="Open Project",
            filetypes=[("E2 HUD Project", f"*{config.PROJECT_EXTENSION}"), ("JSON", "*.json")],
        )
        if not path:
            return
        self.project = load_project(path)
        self.project_path = path
        self.is_dirty = False
        self.canvas_view.set_project(self.project)
        self.res_var.set(self._resolution_label(self.project.resolution))
        self._refresh_layers()
        self._update_status()
        self._history = [self.project.to_dict()]

    def save_project(self) -> None:
        if not self.project_path:
            self.save_project_as()
            return
        save_project(self.project, self.project_path)
        self.is_dirty = False
        self._update_status()

    def save_project_as(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Project",
            defaultextension=config.PROJECT_EXTENSION,
            filetypes=[("E2 HUD Project", f"*{config.PROJECT_EXTENSION}"), ("JSON", "*.json")],
        )
        if not path:
            return
        save_project(self.project, path)
        self.project_path = path
        self.is_dirty = False
        self._update_status()

    def export_hud(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export HUD",
            defaultextension=".txt",
            filetypes=[("Text", "*.txt")],
        )
        if not path:
            return
        exporter = HudExporter(path)
        exporter.export(self.project)
        messagebox.showinfo("Export", "HUD exported successfully.")

    def copy_hud_to_clipboard(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        try:
            exporter = HudExporter(path)
            exporter.export(self.project)
            with open(path, "r", encoding="utf-8") as file:
                data = file.read()
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
        self.root.clipboard_clear()
        self.root.clipboard_append(data)
        self.root.update()
        messagebox.showinfo("Clipboard", "HUD copied to clipboard.")

    def _mark_dirty(self) -> None:
        self.is_dirty = True
        self._update_status()
        self._push_undo_state()

    def _update_status(self) -> None:
        res = self._resolution_label(self.project.resolution)
        zoom = int(self.canvas_view.zoom * 100)
        name = self.project_path if self.project_path else "Untitled"
        dirty = "*" if self.is_dirty else ""
        self.status_var.set(f"{name}{dirty}  |  {res}  |  Zoom {zoom}%")

    def _push_undo_state(self) -> None:
        if self._restoring:
            return
        payload = self.project.to_dict()
        if self._history and self._history[-1] == payload:
            return
        self._history.append(payload)
        if len(self._history) > 50:
            self._history.pop(0)

    def undo(self) -> None:
        if len(self._history) < 2:
            return
        prev_zoom = self.canvas_view.zoom
        prev_pan_x = self.canvas_view.pan_x
        prev_pan_y = self.canvas_view.pan_y
        self._restoring = True
        self._history.pop()
        payload = self._history[-1]
        self.project = Project.from_dict(payload)
        self.canvas_view.set_project(self.project, fit_view=False, redraw=False)
        self.canvas_view.zoom = prev_zoom
        self.canvas_view.pan_x = prev_pan_x
        self.canvas_view.pan_y = prev_pan_y
        self.canvas_view.draw()
        self.res_var.set(self._resolution_label(self.project.resolution))
        self._refresh_layers()
        self.is_dirty = True
        self._update_status()
        self._restoring = False

    def _confirm_discard(self) -> bool:
        if not self.is_dirty:
            return True
        return messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Continue?")

    def show_about(self) -> None:
        messagebox.showinfo("About", "E2 HUD Designer\nModern HUD layout tool for Garry's Mod EGP.")


def run_app() -> None:
    app = EgpApp()
    app.run()

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import uuid

Point = Tuple[float, float]


@dataclass
class Shape:
    id: str
    kind: str
    points: List[Point]
    stroke: str
    stroke_width: int
    fill: Optional[str] = None
    text: str = ""
    font: str = ""
    font_size: int = 12
    align: str = "left"

    def to_dict(self) -> Dict:
        """Description: To dict
        Inputs: None
        """
        return {
            "id": self.id,
            "kind": self.kind,
            "points": self.points,
            "stroke": self.stroke,
            "stroke_width": self.stroke_width,
            "fill": self.fill,
            "text": self.text,
            "font": self.font,
            "font_size": self.font_size,
            "align": self.align,
        }

    @classmethod
    def from_dict(cls, payload: Dict) -> "Shape":
        """Description: From dict
        Inputs: cls, payload: Dict
        """
        return cls(
            id=payload["id"],
            kind=payload["kind"],
            points=[tuple(p) for p in payload.get("points", [])],
            stroke=payload.get("stroke", "#FFFFFF"),
            stroke_width=int(payload.get("stroke_width", 1)),
            fill=payload.get("fill"),
            text=payload.get("text", ""),
            font=payload.get("font", ""),
            font_size=int(payload.get("font_size", 12)),
            align=payload.get("align", "left"),
        )


@dataclass
class Layer:
    id: str
    name: str
    visible: bool = True
    locked: bool = False
    color: str | None = None
    shapes: List[Shape] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Description: To dict
        Inputs: None
        """
        return {
            "id": self.id,
            "name": self.name,
            "visible": self.visible,
            "locked": self.locked,
            "color": self.color,
            "shapes": [shape.to_dict() for shape in self.shapes],
        }

    @classmethod
    def from_dict(cls, payload: Dict) -> "Layer":
        """Description: From dict
        Inputs: cls, payload: Dict
        """
        return cls(
            id=payload["id"],
            name=payload.get("name", "Layer"),
            visible=bool(payload.get("visible", True)),
            locked=bool(payload.get("locked", False)),
            color=payload.get("color"),
            shapes=[Shape.from_dict(item) for item in payload.get("shapes", [])],
        )


@dataclass
class InputDef:
    name: str
    type: str

    def to_dict(self) -> Dict:
        """Description: To dict
        Inputs: None
        """
        return {"name": self.name, "type": self.type}

    @classmethod
    def from_dict(cls, payload: Dict) -> "InputDef":
        """Description: From dict
        Inputs: cls, payload: Dict
        """
        return cls(name=payload.get("name", ""), type=payload.get("type", "Normal"))


@dataclass
class Project:
    resolution: Tuple[int, int]
    layers: List[Layer]
    active_layer_id: str
    inputs: List[InputDef] = field(default_factory=list)

    @classmethod
    def new(cls, resolution: Tuple[int, int]) -> "Project":
        """Description: New
        Inputs: cls, resolution: Tuple[int, int]
        """
        layer = Layer(id=str(uuid.uuid4()), name="Layer 1")
        return cls(resolution=resolution, layers=[layer], active_layer_id=layer.id, inputs=[])

    def to_dict(self) -> Dict:
        """Description: To dict
        Inputs: None
        """
        return {
            "resolution": list(self.resolution),
            "active_layer_id": self.active_layer_id,
            "layers": [layer.to_dict() for layer in self.layers],
            "inputs": [input_def.to_dict() for input_def in self.inputs],
        }

    @classmethod
    def from_dict(cls, payload: Dict) -> "Project":
        """Description: From dict
        Inputs: cls, payload: Dict
        """
        resolution = tuple(payload.get("resolution", (1920, 1080)))
        layers = [Layer.from_dict(item) for item in payload.get("layers", [])]
        active_layer_id = payload.get("active_layer_id")
        inputs = [InputDef.from_dict(item) for item in payload.get("inputs", [])]
        if not layers:
            layers = [Layer(id=str(uuid.uuid4()), name="Layer 1")]
            active_layer_id = layers[0].id
        if active_layer_id is None:
            active_layer_id = layers[0].id
        return cls(resolution=resolution, layers=layers, active_layer_id=active_layer_id, inputs=inputs)

    def get_layer(self, layer_id: str) -> Optional[Layer]:
        """Description: Get layer
        Inputs: layer_id: str
        """
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        return None

    def new_shape_id(self) -> str:
        """Description: New shape id
        Inputs: None
        """
        return str(uuid.uuid4())

import json
from typing import Optional

from model import Project


def save_project(project: Project, path: str) -> None:
    """Description: Save project
    Inputs: project: Project, path: str
    """
    payload = project.to_dict()
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def load_project(path: str) -> Project:
    """Description: Load project
    Inputs: path: str
    """
    with open(path, "r", encoding="utf-8") as file:
        payload = json.load(file)
    return Project.from_dict(payload)

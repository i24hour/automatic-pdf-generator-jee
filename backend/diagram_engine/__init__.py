"""
Diagram Engine Module
Dynamically generates LaTeX/TikZ diagrams based on structured JSON input.
"""

from .generator import DiagramGenerator
from .registry import DiagramRegistry

__all__ = ["DiagramGenerator", "DiagramRegistry"]

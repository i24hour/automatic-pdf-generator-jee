import os
import jinja2
from typing import Dict, Any, Optional
from pydantic import ValidationError

from .registry import DiagramRegistry

class DiagramGenerationError(Exception):
    pass

class DiagramGenerator:
    """
    Main engine to generate LaTeX/TikZ code from parameters.
    """
    
    def __init__(self):
        # Setup Jinja2 Environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            block_start_string='\\BLOCK{',
            block_end_string='}',
            variable_start_string='\\VAR{',
            variable_end_string='}',
            comment_start_string='\\#{',
            comment_end_string='}',
            line_statement_prefix='%%',
            line_comment_prefix='%#',
            trim_blocks=True,
            autoescape=False,
        )

    def generate(self, diagram_type: str, parameters: Dict[str, Any]) -> str:
        """
        Validates input and renders the LaTeX snippet.
        """
        config = DiagramRegistry.get_config(diagram_type)
        if not config:
            raise DiagramGenerationError(f"Unsupported diagram type: {diagram_type}")

        # 1. Validate Parameters via Pydantic
        SchemaClass = config["schema"]
        try:
            validated_params = SchemaClass(**parameters)
        except ValidationError as e:
            raise DiagramGenerationError(f"Invalid parameters for {diagram_type}: {e}")

        # 2. Load Template
        template_name = config["template"]
        try:
            template = self.env.get_template(template_name)
        except jinja2.TemplateNotFound:
            raise DiagramGenerationError(f"Template not found: {template_name}")

        # 3. Render
        try:
            latex_code = template.render(p=validated_params)
            return latex_code
        except Exception as e:
            raise DiagramGenerationError(f"Rendering error: {e}")

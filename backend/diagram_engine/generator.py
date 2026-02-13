import os
import jinja2
import subprocess
import tempfile
import shutil
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

    def render_to_svg(self, diagram_type: str, parameters: Dict[str, Any]) -> str:
        """
        Generates LaTeX, compiles to PDF, converts to SVG.
        """
        # 1. Get snippet
        snippet = self.generate(diagram_type, parameters)
        
        # 2. Wrap in standalone document
        wrapped_tex = f"""
\\documentclass[tikz, border=2pt]{{standalone}}
\\usepackage{{tikz}}
\\usetikzlibrary{{arrows.meta, calc, decorations.pathmorphing, patterns, shapes.geometric}}
\\usepackage{{amsmath}}
\\begin{{document}}
    {snippet}
\\end{{document}}
"""
        
        # 3. Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            tex_path = os.path.join(temp_dir, "diagram.tex")
            pdf_path = os.path.join(temp_dir, "diagram.pdf")
            svg_path = os.path.join(temp_dir, "diagram.svg")
            
            with open(tex_path, "w") as f:
                f.write(wrapped_tex)
            
            # 4. Compile with pdflatex
            try:
                subprocess.check_output(
                    ["pdflatex", "-interaction=nonstopmode", "-output-directory", temp_dir, tex_path],
                    stderr=subprocess.STDOUT
                )
            except subprocess.CalledProcessError as e:
                # Read log file if available
                log_content = "Details unavailable"
                log_path = os.path.join(temp_dir, "diagram.log")
                if os.path.exists(log_path):
                    with open(log_path, "r") as f:
                        log_content = f.read()
                raise DiagramGenerationError(f"LaTeX Compilation Failed:\\n{e.output.decode('utf-8', errors='ignore')}\\nLOG:\\n{log_content}")
            
            # 5. Convert to SVG
            try:
                subprocess.check_output(
                    ["pdf2svg", pdf_path, svg_path],
                    stderr=subprocess.STDOUT
                )
            except subprocess.CalledProcessError as e:
                raise DiagramGenerationError(f"PDF to SVG Conversion Failed: {e.output.decode('utf-8', errors='ignore')}")
            except FileNotFoundError:
                 raise DiagramGenerationError("pdf2svg not installed. Please install it to render diagrams.")

            # 6. Read SVG
            if os.path.exists(svg_path):
                with open(svg_path, "r") as f:
                    return f.read()
            else:
                raise DiagramGenerationError("SVG file was not created.")

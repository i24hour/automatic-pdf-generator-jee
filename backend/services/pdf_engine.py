"""
PDF Engine Service
Renders LaTeX templates with Jinja2 and compiles to PDF using pdflatex.
"""

import os
import subprocess
import tempfile
import shutil
from typing import Dict, Any, Optional
import jinja2


class PDFEngine:
    """PDF generation engine using Jinja2 + pdflatex."""
    
    def __init__(self):
        # Get the backend directory (parent of services/)
        services_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(services_dir)
        
        # Alternative: use /app in Docker
        if os.path.exists("/app/templates"):
            backend_dir = "/app"
        
        self.template_dir = os.path.join(backend_dir, "templates")
        self.output_dir = os.path.join(backend_dir, "output")
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Setup Jinja2 environment with LaTeX-friendly delimiters
        self.jinja_env = jinja2.Environment(
            block_start_string=r'\BLOCK{',
            block_end_string='}',
            variable_start_string=r'\VAR{',
            variable_end_string='}',
            comment_start_string=r'\#{',
            comment_end_string='}',
            line_statement_prefix='%%',
            line_comment_prefix='%#',
            trim_blocks=True,
            autoescape=False,
            loader=jinja2.FileSystemLoader(self.template_dir)
        )
    
    def render_template(self, data: Dict[str, Any]) -> str:
        """
        Render the LaTeX template with the provided data.
        
        Args:
            data: Dictionary containing subject, topic, and questions
            
        Returns:
            Rendered LaTeX string
        """
        template = self.jinja_env.get_template("master.tex")
        
        rendered = template.render(
            subject=data.get("subject", ""),
            topic=data.get("topic", ""),
            level=data.get("level", "JEE Mains"),
            difficulty=data.get("difficulty", "Medium"),
            total_questions=len(data.get("questions", [])),
            questions=data.get("questions", [])
        )
        
        return rendered
    
    def compile_pdf(self, latex_content: str, filename: str = "test_paper") -> Optional[str]:
        """
        Compile LaTeX content to PDF.
        
        Args:
            latex_content: The rendered LaTeX string
            filename: Base filename for the output (without extension)
            
        Returns:
            Path to the generated PDF file, or None if compilation failed
        """
        # Create a temporary directory for compilation
        temp_dir = tempfile.mkdtemp()
        tex_path = os.path.join(temp_dir, f"{filename}.tex")
        pdf_path = os.path.join(temp_dir, f"{filename}.pdf")
        
        try:
            # Write LaTeX content to temporary file
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(latex_content)
            
            # Run pdflatex twice (for references and TOC)
            for _ in range(2):
                result = subprocess.run(
                    [
                        "pdflatex",
                        "-interaction=nonstopmode",
                        "-output-directory", temp_dir,
                        tex_path
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            
            # Check if PDF was generated
            if os.path.exists(pdf_path):
                # Move PDF to output directory
                output_path = os.path.join(self.output_dir, f"{filename}.pdf")
                shutil.copy2(pdf_path, output_path)
                return output_path
            else:
                print(f"PDF compilation failed. pdflatex output:\n{result.stdout}\n{result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("PDF compilation timed out")
            return None
        except FileNotFoundError:
            print("pdflatex not found. Please install texlive.")
            return None
        except Exception as e:
            print(f"PDF compilation error: {str(e)}")
            return None
        finally:
            # Cleanup temporary directory
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
    
    def generate_pdf(self, data: Dict[str, Any], filename: str = "test_paper") -> Optional[str]:
        """
        Generate PDF from question data.
        
        Args:
            data: Dictionary containing subject, topic, and questions
            filename: Base filename for the output
            
        Returns:
            Path to the generated PDF file, or None if generation failed
        """
        # Render template
        latex_content = self.render_template(data)
        
        # Compile to PDF
        pdf_path = self.compile_pdf(latex_content, filename)
        
        return pdf_path


# Singleton instance
pdf_engine = PDFEngine()

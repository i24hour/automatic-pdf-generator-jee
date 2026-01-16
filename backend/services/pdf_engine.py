"""
PDF Engine Service
Renders LaTeX templates with Jinja2 and compiles to PDF using pdflatex.
"""

import os
import subprocess
import tempfile
import shutil
import re
from typing import Dict, Any, Optional
import jinja2


def sanitize_for_latex(text: str) -> str:
    """
    Sanitize text to be LaTeX-safe by escaping problematic Unicode characters.
    Preserves spacing and handles mathematical expressions.
    """
    if not isinstance(text, str):
        return str(text) if text else ""
    
    # First, ensure valid UTF-8
    text = text.encode('utf-8', errors='ignore').decode('utf-8')
    
    # Escape LaTeX special characters FIRST (before other replacements)
    # These need to be escaped: # $ % & _ { } ~ ^ \
    latex_escapes = {
        '#': r'\#',
        '%': r'\%',
        '&': r'\&',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    
    # Don't escape $ and \ as they're used for math mode
    for char, escape in latex_escapes.items():
        # Only escape if not already in a math context
        text = text.replace(char, escape)
    
    # Map problematic Unicode chars to LaTeX equivalents
    replacements = {
        '°': r'$^{\circ}$',
        '×': r'$\times$',
        '÷': r'$\div$',
        '±': r'$\pm$',
        '≈': r'$\approx$',
        '≠': r'$\neq$',
        '≤': r'$\leq$',
        '≥': r'$\geq$',
        '→': r'$\rightarrow$',
        '←': r'$\leftarrow$',
        '↔': r'$\leftrightarrow$',
        '∞': r'$\infty$',
        'α': r'$\alpha$',
        'β': r'$\beta$',
        'γ': r'$\gamma$',
        'δ': r'$\delta$',
        'θ': r'$\theta$',
        'λ': r'$\lambda$',
        'μ': r'$\mu$',
        'π': r'$\pi$',
        'σ': r'$\sigma$',
        'ω': r'$\omega$',
        'Ω': r'$\Omega$',
        'Δ': r'$\Delta$',
        '√': r'$\sqrt{}$',
        '∫': r'$\int$',
        '∑': r'$\sum$',
        '∏': r'$\prod$',
        '∂': r'$\partial$',
        '∈': r'$\in$',
        '∉': r'$\notin$',
        '⊂': r'$\subset$',
        '⊃': r'$\supset$',
        '∪': r'$\cup$',
        '∩': r'$\cap$',
        '∅': r'$\emptyset$',
        '⇒': r'$\Rightarrow$',
        '⇔': r'$\Leftrightarrow$',
        '′': "'",
        '″': "''",
        '–': '--',
        '—': '---',
        '"': "``",
        '"': "''",
        ''': "'",
        ''': "'",
        '…': '...',
        '•': r'$\bullet$',
        '·': r'$\cdot$',
        '½': r'$\frac{1}{2}$',
        '⅓': r'$\frac{1}{3}$',
        '¼': r'$\frac{1}{4}$',
        '¾': r'$\frac{3}{4}$',
        '²': r'$^2$',
        '³': r'$^3$',
        '¹': r'$^1$',
        '₀': r'$_0$',
        '₁': r'$_1$',
        '₂': r'$_2$',
        '₃': r'$_3$',
        # Accented characters - replace with ASCII equivalents
        'Ö': 'O', 'Ü': 'U', 'ö': 'o', 'ü': 'u',
        'ä': 'a', 'Ä': 'A', 'ß': 'ss',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'à': 'a', 'â': 'a', 'ù': 'u', 'û': 'u',
        'ç': 'c', 'ñ': 'n', 'í': 'i', 'ó': 'o',
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    # Replace remaining non-ASCII with space (preserve word boundaries)
    # This keeps spacing intact instead of concatenating words
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    
    # Clean up multiple spaces
    text = re.sub(r' +', ' ', text)
    
    return text


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
        # Choose template based on whether it's an institute request
        is_institute = data.get("is_institute", False)
        template_name = "institute_master.tex" if is_institute else "master.tex"
        
        try:
            template = self.jinja_env.get_template(template_name)
        except Exception:
            # Fallback to master.tex
            template = self.jinja_env.get_template("master.tex")
        
        # Sanitize all question fields for LaTeX safety
        questions = data.get("questions", [])
        sanitized_questions = []
        for q in questions:
            sanitized_q = {}
            for key, value in q.items():
                if isinstance(value, str):
                    sanitized_q[key] = sanitize_for_latex(value)
                elif isinstance(value, list):
                    # Handle options list
                    sanitized_q[key] = [sanitize_for_latex(v) if isinstance(v, str) else v for v in value]
                else:
                    sanitized_q[key] = value
            sanitized_questions.append(sanitized_q)
        
        rendered = template.render(
            subject=sanitize_for_latex(data.get("subject", "")),
            topic=sanitize_for_latex(data.get("topic", "")),
            level=sanitize_for_latex(data.get("level", "JEE Mains")),
            difficulty=sanitize_for_latex(data.get("difficulty", "Medium")),
            total_questions=len(sanitized_questions),
            questions=sanitized_questions,
            # Institute branding
            institute_name=sanitize_for_latex(data.get("institute_name", "")),
            institute_contact=sanitize_for_latex(data.get("institute_contact", "")),
            institute_email=sanitize_for_latex(data.get("institute_email", "")),
            is_institute=is_institute
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
            # Sanitize LaTeX content to ensure valid UTF-8
            # Remove any non-UTF-8 characters that might come from LLM
            latex_content = latex_content.encode('utf-8', errors='ignore').decode('utf-8')
            
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

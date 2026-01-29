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


def escape_latex_outside_math(text: str) -> str:
    """
    Escape special LaTeX characters in text, but PRESERVE math mode content.
    Handles both inline $...$ and block $$...$$ math modes correctly.
    """
    if not text:
        return text
    
    # Use regex to find all math regions:
    # 1. Block math: $$ ... $$
    # 2. Inline math: $ ... $
    # 3. Explicit environments: \begin{...} ... \end{...} (using backreference \2 to match end tag)
    # 4. Use (?s) flag to ensure . matches newlines (crucial for matrices)
    math_pattern = r'(?s)(\$\$.*?\$\$|\\begin\{([a-zA-Z]+\*?)\}.*?\\end\{\2\}|\$[^$]+?\$)'
    
    result = []
    last_end = 0
    
    for match in re.finditer(math_pattern, text):
        # Process content BEFORE this math block (non-math text)
        non_math_part = text[last_end:match.start()]
        if non_math_part:
            # Escape & and # which are problematic outside math
            escaped = non_math_part.replace('#', r'\#').replace('&', r'\&')
            result.append(escaped)
        
        # Process the math block itself (preserve as is)
        result.append(match.group(0))  # group(0) is the full match, ignoring subgroups
        
        last_end = match.end()
        
    # Process remaining text after the last math block
    remaining_part = text[last_end:]
    if remaining_part:
        escaped = remaining_part.replace('#', r'\#').replace('&', r'\&')
        result.append(escaped)
    
    return ''.join(result)

def sanitize_for_latex(text: str) -> str:
    """
    Sanitize text to be LaTeX-safe by escaping problematic Unicode characters.
    Preserves spacing and handles mathematical expressions using robust parsing.
    """
    if not isinstance(text, str):
        return str(text) if text else ""
    
    # First, ensure valid UTF-8
    text = text.encode('utf-8', errors='ignore').decode('utf-8')
    
    # Use robust escaping for & and # (respecting math mode)
    text = escape_latex_outside_math(text)
    
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
        # Greater/Less than symbols (commonly used in ordering)
        '¿': r'$>$',  # Sometimes LLM generates this instead of >
        '›': r'$>$',  # Single right-pointing angle quotation
        '‹': r'$<$',  # Single left-pointing angle quotation
        '>': r'$>$',  # Regular greater-than (for math safety)
        '<': r'$<$',  # Regular less-than (for math safety)
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
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    
    # Clean up multiple spaces
    text = re.sub(r' +', ' ', text)
    
    return text


import ast

def format_answer(answer: Any, q_type: str = 'mcq') -> str:
    """
    Format and validate answer key entries.
    Handles cleanup of list strings "['A', 'B']" and invalid options.
    """
    if answer is None:
        return ""
        
    # Handle numbers (Numerical/Integer)
    if q_type in ['numerical', 'integer', 'short_answer', 'long_answer']:
        return str(answer)
        
    # Handle MCQs (Single/Multi)
    # 1. Parse into list
    options = []
    if isinstance(answer, list):
        options = answer
    elif isinstance(answer, str):
        answer = answer.strip()
        # Try parsing python list string
        if answer.startswith('[') and answer.endswith(']'):
            try:
                parsed = ast.literal_eval(answer)
                if isinstance(parsed, list):
                    options = parsed
            except:
                # Fallback: remove brackets and split
                options = answer.replace('[','').replace(']','').replace("'", "").replace('"', "").split(',')
        else:
            # Comma separated string or single letter
            options = answer.split(',') if ',' in answer else list(answer) if len(answer) > 1 and answer.isupper() else [answer]
            
    # 2. Clean and Filter Options
    valid_options = {'A', 'B', 'C', 'D'}
    cleaned_options = []
    
    for opt in options:
        opt_str = str(opt).strip().upper().replace("'", "").replace('"', "")
        # Remove empty
        if not opt_str:
            continue
            
        # For standard MCQs, only allow A, B, C, D matches
        # Use regex to check if it's strictly a letter choice
        if re.match(r'^[A-Z]$', opt_str):
            if opt_str in valid_options:
                cleaned_options.append(opt_str)
            else:
                # Invalid option like 'E', 'F' - User hated this.
                # However, if it's "Bonus", keep it? Assuming mainly standard.
                # If strictly E, ignore it.
                pass
        else:
            # Might be "All", "Bonus", or numeric fallback?
            # If it's something like "BCD", split it?
            # "BCD" -> B, C, D
            if re.match(r'^[A-D]+$', opt_str):
                for char in opt_str:
                    if char in valid_options:
                        cleaned_options.append(char)
            else:
                # Keep complex answers as is (e.g. "Bonus")
                cleaned_options.append(opt_str)
                
    # Deduplicate and Sort
    cleaned_options = sorted(list(set(cleaned_options)))
    
    return ", ".join(cleaned_options)


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
                if key == "answer":
                    # Special formatting for answers
                    sanitized_q[key] = format_answer(value, q.get("type", "mcq"))
                    # Still sanitize for latex safety just in case
                    sanitized_q[key] = sanitize_for_latex(sanitized_q[key])
                elif isinstance(value, str):
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
            is_institute=is_institute,
            include_solutions=data.get("include_solutions", False)
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
            
            # Run pdflatex (single run is enough for test papers without TOC)
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-output-directory", temp_dir,
                    tex_path
                ],
                capture_output=True,
                text=True,
                timeout=180  # Increased timeout for large papers
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

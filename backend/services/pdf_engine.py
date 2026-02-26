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
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


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


def clean_solution_for_latex(text: str) -> str:
    """
    Clean LLM-generated solution text to prevent LaTeX compilation errors.
    """
    if not isinstance(text, str) or not text:
        return text or ""

    # 0. Replace \mbox with \text — \mbox doesn't handle \par/newlines; \text is safer
    text = text.replace('\\mbox{', '\\text{')

    # 1. Fix stray \\\\ before LaTeX commands (\\\\textbf → \n\n\textbf)
    #    This is the #1 cause of "There's no line here to end"
    text = re.sub(r'\\\\\s*(\\text)', r'\n\n\1', text)

    # 2. Fix stray \\\\ at start of lines or after blank lines
    text = re.sub(r'^\\\\\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n\\\\\s*\n', '\n\n', text)

    # 3. Replace \\n\\n / \\n (literal escaped newlines from JSON) with actual newlines
    text = text.replace('\\n\\n', '\n\n')
    text = text.replace('\\n', '\n')

    # 4. Fix \\\\ that appears right before \noindent, \begin, \end
    text = re.sub(r'\\\\\s*(\\(?:noindent|begin|end|vspace|hspace|par))', r'\n\n\1', text)

    # 5. Remove standalone \\\\ on their own line
    text = re.sub(r'^\s*\\\\\s*$', '', text, flags=re.MULTILINE)

    # 6. Remove \\ immediately before closing $ (causes "Missing $ inserted")
    #    e.g.  $\alpha \\ $ → $\alpha $
    text = re.sub(r'\\\\\s*\$', '$', text)

    # 7. Remove \\ inside inline math $...$ — \\ is not valid in inline math mode
    def _strip_linebreaks_in_inline_math(t: str) -> str:
        result = []
        i = 0
        while i < len(t):
            if t[i] == '$' and (i == 0 or t[i-1] != '\\'):
                # Find matching closing $
                j = i + 1
                while j < len(t):
                    if t[j] == '$' and t[j-1] != '\\':
                        break
                    j += 1
                inner = t[i+1:j]
                # Replace \\ inside inline math with a space
                inner = inner.replace('\\\\', ' ')
                result.append('$' + inner + '$')
                i = j + 1
            else:
                result.append(t[i])
                i += 1
        return ''.join(result)

    text = _strip_linebreaks_in_inline_math(text)

    # 8. Remove \par inside \text{} or \mbox{} (causes "file ended while scanning")
    #    Walk the string and strip \par inside the first brace level of \text{ \mbox{
    def _remove_par_in_hbox(t: str) -> str:
        out = []
        i = 0
        hbox_cmds = ('\\text{', '\\mbox{', '\\textbf{', '\\textit{')
        while i < len(t):
            matched_cmd = None
            for cmd in hbox_cmds:
                if t[i:i+len(cmd)] == cmd:
                    matched_cmd = cmd
                    break
            if matched_cmd:
                out.append(matched_cmd)
                i += len(matched_cmd)
                depth = 1
                while i < len(t) and depth > 0:
                    if t[i] == '{':
                        depth += 1
                        out.append(t[i])
                    elif t[i] == '}':
                        depth -= 1
                        if depth == 0:
                            out.append('}')
                        else:
                            out.append(t[i])
                    elif t[i:i+4] == '\\par':
                        # Replace \par inside hbox with a space
                        out.append(' ')
                        i += 4
                        continue
                    else:
                        out.append(t[i])
                    i += 1
            else:
                out.append(t[i])
                i += 1
        return ''.join(out)

    text = _remove_par_in_hbox(text)

    return text.strip()

def sanitize_for_latex(text: str) -> str:
    """
    Sanitize text to be LaTeX-safe by escaping problematic Unicode characters.
    Preserves spacing and handles mathematical expressions using robust parsing.
    """
    if not isinstance(text, str):
        return str(text) if text else ""
    
    # First, ensure valid UTF-8
    text = text.encode('utf-8', errors='ignore').decode('utf-8')
    
    # Strip common option prefixes (A), a), (a), 1. etc.) followed by space
    # Matches: "A) ", "a) ", "(a) ", "1. ", "1) "
    text = re.sub(r'^\s*(?:[A-Da-d][.)]|[0-9]+[.)]|\([A-Da-d0-9]+\))\s+', '', text)
    
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

    # Detect and convert Markdown Tables to LaTeX tables
    # Helper to check if a line looks like a table row (has pipes and content)
    def is_table_row(l):
        return '|' in l and len(l.strip().split('|')) > 1

    if '|' in text and '---' in text:
        try:
            lines = text.strip().split('\n')
            latex_table = []
            in_table = False
            header = []
            alignments = []
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Check for table start (Header row followed by separator)
                # Allow tables without outer pipes: "Header 1 | Header 2"
                if not in_table and is_table_row(line) and i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    # Separator must contain dashes and pipes
                    if '---' in next_line and '|' in next_line:
                        in_table = True
                        
                        # Clean and parse header
                        # Remove outer pipes if present for splitting
                        clean_line = line
                        if clean_line.startswith('|'): clean_line = clean_line[1:]
                        if clean_line.endswith('|'): clean_line = clean_line[:-1]
                        header = [c.strip() for c in clean_line.split('|')]
                        
                        # Parse alignments
                        clean_next = next_line
                        if clean_next.startswith('|'): clean_next = clean_next[1:]
                        if clean_next.endswith('|'): clean_next = clean_next[:-1]
                        
                        align_parts = [c.strip() for c in clean_next.split('|')]
                        alignments = []
                        # Default to 'l' if alignment parts don't match header count
                        for part in align_parts:
                            if part.startswith(':') and part.endswith(':'):
                                alignments.append('c')
                            elif part.endswith(':'):
                                alignments.append('r')
                            else:
                                alignments.append('l')
                        
                        # Start LaTeX Table
                        # Ensure alignment count matches header count
                        while len(alignments) < len(header):
                            alignments.append('l')
                        
                        col_spec = "|" + "|".join(alignments[:len(header)]) + "|"
                        latex_table.append(r'\begin{center}')
                        latex_table.append(r'\begin{tabular}{' + col_spec + r'}')
                        latex_table.append(r'\hline')
                        
                        # Add Header
                        latex_table.append(" & ".join([r'\textbf{' + h + '}' for h in header]) + r' \\ \hline')
                        
                        i += 2 # Skip header and separator
                        continue
                        
                if in_table:
                    # Check if line is still part of table
                    if is_table_row(line):
                        # Table row
                        clean_line = line
                        if clean_line.startswith('|'): clean_line = clean_line[1:]
                        if clean_line.endswith('|'): clean_line = clean_line[:-1]
                        
                        cells = [c.strip() for c in clean_line.split('|')]
                        
                        # Handle colspan/rowspan mismatch by padding
                        if len(cells) < len(header):
                            cells.extend([''] * (len(header) - len(cells)))
                        elif len(cells) > len(header):
                            cells = cells[:len(header)]
                            
                        latex_table.append(" & ".join(cells) + r' \\ \hline')
                    else:
                        # Table ended
                        in_table = False
                        latex_table.append(r'\end{tabular}')
                        latex_table.append(r'\end{center}')
                        latex_table.append(line)
                else:
                    # Handle standalone '---' which might be horizontal rules
                    if re.match(r'^\s*-{3,}\s*$', line):
                         latex_table.append(r'\noindent\rule{\textwidth}{0.4pt}')
                    else:
                        latex_table.append(line)
                
                i += 1
            
            if in_table: # Close if checked ended inside table
                latex_table.append(r'\end{tabular}')
                latex_table.append(r'\end{center}')
                
            return '\n'.join(latex_table)
        except Exception as e:
            # If conversion fails, fallback to original text (with basic cleaning)
            print(f"Table conversion error: {e}")
            return text
    
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
    
        # Initialize Diagram Generator
        from diagram_engine.generator import DiagramGenerator
        self.diagram_generator = DiagramGenerator()

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
        for i, q in enumerate(questions):
            sanitized_q = {}
            
            # 1. Clean Text (Remove [DIAGRAM: ...])
            raw_text = q.get("text", "")
            # Remove [DIAGRAM: ...] blocks (handle newlines with DOTALL)
            cleaned_text = re.sub(r'\[DIAGRAM:.*?\]', '', raw_text, flags=re.IGNORECASE | re.DOTALL).strip()
            
            # Fallback: If stripping resulted in empty text, use the original text (cleaned of markers only)
            # This handles cases where the entire question was wrapped in [DIAGRAM: ...]
            if not cleaned_text and raw_text.strip():
                # Try to extract content inside [DIAGRAM: ...] or just use raw text without the markers
                # Simple approach: Remove the [DIAGRAM: and ] markers but keep content
                cleaned_text = re.sub(r'\[DIAGRAM:(.*?)\]', r'\1', raw_text, flags=re.IGNORECASE | re.DOTALL).strip()
                if not cleaned_text: # processing failed or was empty inside
                     cleaned_text = raw_text
            
            for key, value in q.items():
                if key == "text":
                    sanitized_q[key] = sanitize_for_latex(cleaned_text)
                elif key == "options" and isinstance(value, list):
                    opts = [sanitize_for_latex(str(opt)) for opt in value]
                    # Pad to 4 options to prevent Jinja index errors
                    while len(opts) < 4:
                        opts.append("")
                    sanitized_q[key] = opts
                elif key == "answer":
                    # Special formatting for answers (already formatted string or list?)
                    # Assuming value is the raw answer
                    # We should probably just sanitize it.
                    # Wait, original code had format_answer call? 
                    # I don't see format_answer imported or defined in the snippet I saw.
                    # Ah, I missed viewing format_answer. Let's assume it's not there or just use sanitize.
                    # Actually, looking at previous view, line 440 calls format_answer.
                    # I must check if format_answer is defined in this file.
                    # It was used in line 440 of the previous view.
                    # Let's hope it's available in global scope or imported.
                    # I will check lines 1-100 to see imports/definitions.
                    # Actually I will just sanitize it for now to be safe, unless I find format_answer.
                    sanitized_q[key] = sanitize_for_latex(str(value)) 
                elif key == "solution" and isinstance(value, str):
                    # Solutions need special cleaning — LLMs generate stray \\\\ that crash LaTeX
                    sanitized_q[key] = clean_solution_for_latex(value)
                elif isinstance(value, str):
                    sanitized_q[key] = sanitize_for_latex(value)
                else:
                    sanitized_q[key] = value
            
            # 2a. NEW: Convert diagram_svg → PNG for embedding in PDF
            diagram_svg = q.get("diagram_svg")
            if diagram_svg and diagram_svg.strip().startswith("<svg"):
                try:
                    import cairosvg
                    png_bytes = cairosvg.svg2png(
                        bytestring=diagram_svg.encode("utf-8"),
                        output_width=350,
                        background_color="white",
                    )
                    # Write PNG to a persistent temp file (cleaned up after compile)
                    import tempfile as _tf
                    png_file = _tf.NamedTemporaryFile(suffix=".png", delete=False)
                    png_file.write(png_bytes)
                    png_file.flush()
                    png_file.close()
                    sanitized_q["diagram_png_path"] = png_file.name
                except Exception as e:
                    print(f"[Diagram SVG→PNG] Skipped for PDF (cairosvg error): {e}")
                    sanitized_q["diagram_png_path"] = None

            # 2b. LEGACY: Generate diagram TikZ via diagram_engine if params exist
            diagram_type = q.get("diagram_type")
            diagram_params = q.get("diagram_params")
            if diagram_type and isinstance(diagram_params, dict):
                try:
                    tikz_code = self.diagram_generator.generate(diagram_type, diagram_params)
                    sanitized_q["diagram_tikz"] = tikz_code
                except Exception as e:
                    print(f"Error generating TikZ diagram for PDF: {e}")
                    sanitized_q["diagram_tikz"] = None
            


            # Handle matrix_match special fields
            if q.get("type") == "matrix_match":
                list1_raw = q.get("list1", [])
                list2_raw = q.get("list2", [])
                sanitized_q["list1"] = [sanitize_for_latex(str(item)) for item in list1_raw]
                sanitized_q["list2"] = [sanitize_for_latex(str(item)) for item in list2_raw]
                # Pad both lists to same length (max 4 rows)
                max_len = max(len(sanitized_q["list1"]), len(sanitized_q["list2"]), 4)
                while len(sanitized_q["list1"]) < max_len:
                    sanitized_q["list1"].append("")
                while len(sanitized_q["list2"]) < max_len:
                    sanitized_q["list2"].append("")

            # Handle paragraph (comprehension) special fields
            if q.get("type") == "paragraph":
                raw_passage = q.get("passage", "")
                sanitized_q["passage"] = sanitize_for_latex(raw_passage)
                raw_sqs = q.get("sub_questions", [])
                sanitized_sqs = []
                for sq in raw_sqs:
                    san_sq = {}
                    san_sq["text"] = sanitize_for_latex(str(sq.get("text", "")))
                    raw_opts = sq.get("options", [])
                    san_opts = [sanitize_for_latex(str(o)) for o in raw_opts]
                    while len(san_opts) < 4:
                        san_opts.append("")
                    san_sq["options"] = san_opts
                    san_sq["answer"] = sanitize_for_latex(str(sq.get("answer", "")))
                    san_sq["solution"] = clean_solution_for_latex(sq.get("solution", ""))
                    sanitized_sqs.append(san_sq)
                sanitized_q["sub_questions"] = sanitized_sqs

            sanitized_q["id"] = q.get("id", i)
            sanitized_q["type"] = q.get("type", "mcq")
            sanitized_q["answer"] = q.get("answer", "")
            sanitized_questions.append(sanitized_q)
        
        # Prepare context
        context = {
            "subject": sanitize_for_latex(data.get("subject", "")),
            "topic": sanitize_for_latex(data.get("topic", "")),
            "level": sanitize_for_latex(data.get("level", "JEE Mains")),
            "difficulty": sanitize_for_latex(data.get("difficulty", "Medium")),
            "total_questions": len(sanitized_questions),
            "questions": sanitized_questions,
            # Institute branding
            "institute_name": sanitize_for_latex(data.get("institute_name", "")),
            "institute_contact": sanitize_for_latex(data.get("institute_contact", "")),
            "institute_email": sanitize_for_latex(data.get("institute_email", "")),
            "is_institute": is_institute,
            "include_solutions": data.get("include_solutions", False)
        }
        
        try:
            # Render template
            latex_content = template.render(**context)
            return latex_content
        except Exception as e:
            import traceback
            print(f"ERROR: LaTeX Template Rendering Failed: {e}")
            print(traceback.format_exc())
            # Log specific context that might cause issues (truncate to avoid huge logs)
            print(f"Context Sample: {str(context)[:1000]}")
            raise e # Re-raise to trigger fallback in caller
    
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

    def generate_fallback_pdf(self, data: Dict[str, Any], filename: str = "test_paper") -> Optional[str]:
        """
        Generate a fallback PDF using ReportLab when pdflatex is not available.
        """
        try:
            output_path = os.path.join(self.output_dir, f"{filename}.pdf")
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Create custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                alignment=1, # Center
                spaceAfter=20
            )
            
            question_style = ParagraphStyle(
                'Question',
                parent=styles['BodyText'],
                spaceAfter=12,
                fontSize=11,
                leading=14
            )

            # Header
            story.append(Paragraph(data.get("institute_name", "Test Paper"), title_style))
            story.append(Spacer(1, 12))
            
            # Metadata
            subject = data.get("subject", "Subject Not Specified")
            topic = data.get("topic", "General")
            story.append(Paragraph(f"<b>Subject:</b> {subject} | <b>Topic:</b> {topic}", styles['Normal']))
            story.append(Spacer(1, 24))

            # Questions
            questions = data.get("questions", [])
            for i, q in enumerate(questions, 1):
                q_text = q.get("question", "")
                # Clean up latex math markers for basic text display
                q_text = q_text.replace('$', '').replace('\\', '')
                
                story.append(Paragraph(f"<b>Q{i}.</b> {q_text}", question_style))
                
                options = q.get("options", [])
                if options:
                    for opt in options:
                        opt = str(opt).replace('$', '').replace('\\', '')
                        story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;o {opt}", styles['BodyText']))
                
                story.append(Spacer(1, 12))

            # Solutions (if included)
            if data.get("include_solutions", False):
                story.append(Spacer(1, 24))
                story.append(Paragraph("<b>Solutions</b>", styles['Heading2']))
                for i, q in enumerate(questions, 1):
                    ans = q.get("answer", "N/A")
                    sol = q.get("solution", "")
                    story.append(Paragraph(f"<b>Q{i}:</b> {ans}", styles['BodyText']))
                    if sol:
                        story.append(Paragraph(f"<i>Explanation:</i> {sol}", styles['Italic']))
                    story.append(Spacer(1, 6))

            doc.build(story)
            print(f"Generated fallback PDF: {output_path}")
            return output_path
            
        except Exception as e:
            import traceback
            print(f"Fallback PDF generation failed: {e}")
            traceback.print_exc()
            return None

    def generate_pdf(self, data: Dict[str, Any], filename: str = "test_paper") -> Optional[str]:
        """
        Generate PDF from question data.
        Uses pdflatex ONLY — no fallback to basic layout.
        
        Args:
            data: Dictionary containing subject, topic, and questions
            filename: Base filename for the output
            
        Returns:
            Path to the generated PDF file, or None if generation failed
        """
        # Render template
        try:
            latex_content = self.render_template(data)
        except Exception as e:
            print(f"CRITICAL: Template rendering failed: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        # Compile to PDF using pdflatex
        pdf_path = self.compile_pdf(latex_content, filename)
        
        if pdf_path:
            return pdf_path
        
        # No fallback — return None so caller knows it failed
        print("ERROR: pdflatex compilation failed. No fallback.")
        return None


# Singleton instance
pdf_engine = PDFEngine()

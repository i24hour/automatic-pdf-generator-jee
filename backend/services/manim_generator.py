"""
Manim Generator - LLM-powered Manim code generation.
Uses LiteLLM for unified LLM interface.
"""

import os
import json
import asyncio
import tempfile
import subprocess
from typing import Dict, Any, List, Optional
from pathlib import Path

import litellm


class ManimGenerator:
    """
    Generates Manim code for mathematical animations using LLM.
    """
    
    # Default model for code generation
    DEFAULT_MODEL = os.getenv("ACTIVE_MODEL", "gemini/gemini-2.5-flash")
    
    # Manim code template
    CODE_TEMPLATE = '''
from manim import *

class MathAnimation(Scene):
    def construct(self):
{scene_code}
'''
    
    # System prompt for Manim code generation
    SYSTEM_PROMPT = """You are a Manim animator. Generate SHORT, SIMPLE Manim Python code that WORKS.

STRICT RULES:
1. scene_code = ONLY the body of construct(). NO imports, NO class, NO def.
2. BANNED (will crash): MathTex, Tex, LaTeX, Brace, NumberPlane, Axes, set_points_by_ends, coords_to_point
3. BANNED IMPORTS: numpy, scipy, math, random — DO NOT USE ANY IMPORT
4. Math symbols: use Text() with Unicode ONLY — e.g. Text("a² + b² = c²"), Text("∫"), Text("θ")

ALLOWED OBJECTS (use ONLY these):
- Text(string, font_size=N, color=COLOR)
- Circle(radius=N, color=COLOR, fill_opacity=N)  
- Square(side_length=N, color=COLOR)
- Rectangle(width=N, height=N, color=COLOR)
- Triangle(color=COLOR, fill_opacity=N) — create with Triangle(), then scale()
- Arrow(start=LEFT, end=RIGHT, color=COLOR)
- Line(start=LEFT, end=RIGHT, color=COLOR)
- Dot(point=ORIGIN, color=COLOR)
- VGroup(obj1, obj2, ...)

ALLOWED ANIMATIONS: Write, FadeIn, FadeOut, Create, GrowArrow, Transform, Indicate

SAFE POSITIONING: .shift(UP/DOWN/LEFT/RIGHT * N), .to_edge(UP/DOWN), .next_to(obj, direction), .scale(N)

WORKING EXAMPLE — copy this exact style:
        title = Text("Pythagorean Theorem", font_size=44, color=BLUE)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))
        triangle = Triangle(color=BLUE, fill_opacity=0.3)
        triangle.scale(2)
        self.play(Create(triangle))
        self.wait(1)
        formula = Text("a² + b² = c²", font_size=40, color=YELLOW)
        formula.shift(DOWN * 2)
        self.play(FadeIn(formula))
        self.wait(2)
        self.play(FadeOut(title), FadeOut(triangle), FadeOut(formula))

OUTPUT — return ONLY this JSON (no extra text):
{
    "scene_code": "        title = Text('Example', font_size=40, color=BLUE)\\n        self.play(Write(title))\\n        self.wait(2)",
    "narration_script": [{"timestamp": 0, "duration": 5, "text": "Narration"}],
    "estimated_duration_seconds": 30,
    "title": "Short Title"
}

CRITICAL: No imports in scene_code. No NumberPlane. No Axes. No set_points_by_ends. Max 30 lines."""

    def __init__(self, model: str = None):
        self.model = model or self.DEFAULT_MODEL

    # Patterns that the LLM hallucinates but DON'T exist in Manim
    BANNED_PATTERNS = [
        ".hypotenuse", ".set_points_by_ends", ".coords_to_point",
        "NumberPlane", "Axes(", "MathTex", "Tex(", "BraceLabel",
        ".get_vertices", ".get_all_points", ".get_anchors",
        "import numpy", "import math", "import scipy", "import random",
        "from numpy", "from math", "from scipy",
    ]

    def check_banned_patterns(self, code: str) -> list:
        """Return list of banned patterns found in the code."""
        found = []
        for pattern in self.BANNED_PATTERNS:
            if pattern in code:
                found.append(pattern)
        return found
    async def generate_animation(
        self,
        topic: str,
        language: str = "en",
        max_duration: int = 60,
        difficulty: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate Manim animation code and narration script.
        
        Args:
            topic: Math topic/question to animate
            language: Language for narration (en/hi)
            max_duration: Maximum video duration in seconds
            difficulty: Difficulty level (easy/medium/hard)
            
        Returns:
            Dict with scene_code, narration_script, etc.
        """
        
        language_instruction = "in English" if language == "en" else "in Hindi (Devanagari script)"
        
        user_prompt = f"""Generate a Manim animation for this math topic:

Topic: {topic}

Requirements:
- Maximum duration: {max_duration} seconds
- Difficulty level: {difficulty}
- Narration language: {language_instruction}
- Make it educational and visually engaging
- Include step-by-step explanations

Generate the animation code and synchronized narration script."""

        try:
            last_error = None
            for attempt in range(3):  # Up to 3 attempts
                messages = [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
                # On retry, prepend the error so LLM knows what to fix
                if last_error and attempt > 0:
                    messages.append({
                        "role": "assistant",
                        "content": f"My previous code had an error: {last_error}. Let me regenerate using ONLY the allowed objects listed. No .hypotenuse, no custom attributes, no imports."
                    })
                    messages.append({
                        "role": "user",
                        "content": "Please regenerate. Use ONLY Text(), Circle(), Square(), Rectangle(), Triangle(), Arrow(), Line() — no other methods."
                    })

                response = await asyncio.to_thread(
                    litellm.completion,
                    model=self.model,
                    messages=messages,
                    temperature=0.3 if attempt > 0 else 0.7,  # Lower temp on retry
                    max_tokens=16384,
                    response_format={"type": "json_object"}
                )

                content = response.choices[0].message.content

                # Parse JSON response
                try:
                    result = json.loads(content)
                except json.JSONDecodeError:
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        result = json.loads(json_match.group())
                    else:
                        last_error = "Failed to parse LLM response as JSON"
                        continue

                # Validate required fields
                required_fields = ["scene_code", "narration_script"]
                for field in required_fields:
                    if field not in result:
                        last_error = f"Missing required field: {field}"
                        continue

                # Build complete Manim code
                scene_code = result["scene_code"]

                # Check for banned patterns — retry if found
                banned_found = self.check_banned_patterns(scene_code)
                if banned_found:
                    last_error = f"Used banned patterns: {', '.join(banned_found)}. These do not exist in Manim."
                    print(f"⚠ Attempt {attempt+1}: banned patterns found: {banned_found} — retrying")
                    continue

                # Check if LLM returned full class definition instead of just method body
                if "class " in scene_code and "def construct" in scene_code:
                    full_code = scene_code
                else:
                    full_code = self.CODE_TEMPLATE.format(scene_code=scene_code)

                return {
                    "success": True,
                    "manim_code": full_code,
                    "narration_script": result["narration_script"],
                    "estimated_duration": result.get("estimated_duration_seconds", max_duration),
                    "title": result.get("title", topic),
                    "model_used": self.model
                }

            # All attempts exhausted
            return {"success": False, "error": f"Code generation failed after 3 attempts. Last error: {last_error}"}

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def auto_fix_code(self, code: str) -> str:
        """
        Attempt to auto-fix common LLM code generation errors.
        Specifically handles: empty function/class bodies (missing 'pass').
        """
        import re
        lines = code.split("\n")
        fixed_lines = []
        for i, line in enumerate(lines):
            fixed_lines.append(line)
            # If this line ends a def/class block with a colon, check if next non-empty line
            # is less indented (empty body)
            stripped = line.rstrip()
            if stripped.endswith(":") and re.match(r'^\s*(def |class |if |else:|elif |for |while |try:|except|finally:)', stripped):
                # Look ahead at the next non-empty line
                next_code_line = None
                for j in range(i + 1, len(lines)):
                    if lines[j].strip():  # non-empty
                        next_code_line = lines[j]
                        break
                
                if next_code_line is not None:
                    current_indent = len(line) - len(line.lstrip())
                    next_indent = len(next_code_line) - len(next_code_line.lstrip())
                    # If next line isn't indented more than current → empty body
                    if next_indent <= current_indent:
                        indent = " " * (current_indent + 8)  # 8 spaces indent (Manim convention)
                        fixed_lines.append(f"{indent}pass")
                elif i == len(lines) - 1:  # Last line of file ends with colon
                    current_indent = len(line) - len(line.lstrip())
                    indent = " " * (current_indent + 8)
                    fixed_lines.append(f"{indent}pass")
        return "\n".join(fixed_lines)

    def validate_code(self, code: str) -> Dict[str, Any]:
        """
        Validate Manim code for syntax errors. Attempts auto-fix before reporting failure.
        """
        # First attempt
        try:
            compile(code, "<string>", "exec")
            return {"success": True, "valid": True, "code": code}
        except SyntaxError:
            pass

        # Try auto-fixing and re-validating
        try:
            fixed = self.auto_fix_code(code)
            compile(fixed, "<string>", "exec")
            print("✓ Code auto-fixed successfully")
            return {"success": True, "valid": True, "code": fixed}  # return fixed code
        except SyntaxError as e:
            return {
                "success": True,
                "valid": False,
                "code": code,
                "error": f"Syntax error at line {e.lineno}: {e.msg}"
            }

    async def render_video(
        self,
        code: str,
        output_dir: str = None,
        quality: str = "medium"
    ) -> Dict[str, Any]:
        """
        Render Manim code to video.
        
        Args:
            code: Manim Python code
            output_dir: Output directory for video
            quality: Video quality (low, medium, high)
            
        Returns:
            Dict with video_path on success
        """
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        
        # Quality flags
        quality_flags = {
            "low": "-ql",     # 480p15
            "medium": "-qm",   # 720p30
            "high": "-qh"      # 1080p60
        }
        
        flag = quality_flags.get(quality, "-qm")
        
        # Write code to temp file
        code_path = os.path.join(output_dir, "scene.py")
        with open(code_path, "w") as f:
            f.write(code)
        
        try:
            # Extract class name from code (dynamically handles LLM-generated class names)
            import re
            class_match = re.search(r'class\s+(\w+)\s*\([^)]*Scene[^)]*\)', code)
            scene_class = class_match.group(1) if class_match else "MathAnimation"
            
            # Run manim command
            process = await asyncio.create_subprocess_exec(
                "manim", code_path, scene_class,
                flag, "-o", "output.mp4",
                "--media_dir", output_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=output_dir
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300  # 5 minute timeout
            )
            
            if process.returncode != 0:
                return {
                    "success": False,
                    "error": f"Manim render failed: {stderr.decode()}"
                }
            
            # Find output video
            video_path = os.path.join(output_dir, "media", "videos", "scene", quality_flags[quality].replace("-q", ""), "output.mp4")
            
            # Alternative path patterns
            if not os.path.exists(video_path):
                for root, dirs, files in os.walk(output_dir):
                    for f in files:
                        if f.endswith(".mp4"):
                            video_path = os.path.join(root, f)
                            break
            
            if os.path.exists(video_path):
                return {
                    "success": True,
                    "video_path": video_path
                }
            else:
                return {
                    "success": False,
                    "error": "Video file not found after rendering"
                }
                
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Render timeout exceeded (5 minutes)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_manim_generator: Optional[ManimGenerator] = None


def get_manim_generator() -> ManimGenerator:
    """Get the global Manim generator instance."""
    global _manim_generator
    if _manim_generator is None:
        _manim_generator = ManimGenerator()
    return _manim_generator


# Test function
async def test_generate():
    """Test Manim code generation."""
    generator = get_manim_generator()
    
    result = await generator.generate_animation(
        topic="Pythagorean theorem: a² + b² = c²",
        language="en",
        max_duration=60
    )
    
    if result["success"]:
        print("✓ Code generated successfully!")
        print(f"  Title: {result['title']}")
        print(f"  Duration: {result['estimated_duration']}s")
        print(f"  Narration segments: {len(result['narration_script'])}")
        print("\n--- Manim Code ---")
        print(result["manim_code"][:500] + "...")
    else:
        print(f"✗ Failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(test_generate())

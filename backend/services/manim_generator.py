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
    SYSTEM_PROMPT = """You are an expert math education animator. Create a FULL EDUCATIONAL VIDEO (45-90 seconds) explaining the topic step by step.

MANDATORY STRUCTURE — every video MUST have ALL of these sections:
1. TITLE (5s): Show topic title with Write animation + self.wait(2)
2. INTRO (8s): Brief intro text, FadeIn + self.wait(3)
3. STEP 1 (10-15s): First concept — shape/formula + explanation text + self.wait(3)
4. STEP 2 (10-15s): Second concept — build on step 1 + self.wait(3)
5. STEP 3 (10-15s): Third concept or proof step + self.wait(3)
6. CONCLUSION (8s): Summary text + self.wait(3)
MINIMUM 8 self.wait() calls. MINIMUM 6 self.play() calls. Target 50+ lines.

STRICT TECHNICAL RULES:
- scene_code = ONLY the body of construct(). NO imports, NO class, NO def.
- BANNED (crash instantly): MathTex, Tex, LaTeX, Brace, NumberPlane, Axes, set_points_by_ends, coords_to_point, .hypotenuse, .get_vertices, .get_anchors
- BANNED IMPORTS: numpy, scipy, math, random, itertools — NOTHING
- Math: ONLY Text() with Unicode — Text("a² + b² = c²"), Text("∫"), Text("∑"), Text("π")

ALLOWED OBJECTS: Text, Circle, Square, Rectangle, Triangle, Arrow, Line, Dot, VGroup
ALLOWED ANIMATIONS: Write, FadeIn, FadeOut, Create, GrowArrow, Transform, Indicate, ReplacementTransform
SAFE METHODS: .shift(UP/DOWN/LEFT/RIGHT * N), .to_edge(UP/DOWN/LEFT/RIGHT), .next_to(obj, direction), .scale(N), .set_color(COLOR), .move_to(point)
COLORS: BLUE, RED, GREEN, YELLOW, WHITE, ORANGE, PURPLE, TEAL, GOLD

POSITIONING PATTERNS (safe to use):
- obj.shift(UP * 2)           ✓
- obj.to_edge(UP)             ✓ 
- obj.next_to(other, DOWN)    ✓
- obj.move_to(ORIGIN)         ✓
- VGroup(a, b).arrange(DOWN)  ✓

WORKING EXAMPLE — Pythagorean Theorem (50 lines, 60 seconds):
        # Title
        title = Text("Pythagorean Theorem", font_size=48, color=BLUE)
        subtitle = Text("a² + b² = c²", font_size=36, color=YELLOW)
        subtitle.next_to(title, DOWN)
        self.play(Write(title))
        self.play(FadeIn(subtitle))
        self.wait(3)
        self.play(FadeOut(title), FadeOut(subtitle))
        # Intro
        intro = Text("In a right triangle:", font_size=36, color=WHITE)
        intro.to_edge(UP)
        self.play(Write(intro))
        self.wait(2)
        # Triangle
        triangle = Triangle(color=BLUE, fill_opacity=0.3)
        triangle.scale(2)
        self.play(Create(triangle))
        self.wait(2)
        # Side labels
        label_a = Text("a", font_size=32, color=RED)
        label_b = Text("b", font_size=32, color=GREEN)
        label_c = Text("c", font_size=32, color=YELLOW)
        label_a.next_to(triangle, LEFT)
        label_b.next_to(triangle, DOWN)
        label_c.next_to(triangle, RIGHT)
        self.play(FadeIn(label_a), FadeIn(label_b), FadeIn(label_c))
        self.wait(2)
        # Formula
        formula = Text("a² + b² = c²", font_size=44, color=YELLOW)
        formula.shift(DOWN * 2.5)
        self.play(Write(formula))
        self.wait(3)
        # Example
        example_title = Text("Example: a=3, b=4, c=5", font_size=32, color=WHITE)
        example_title.to_edge(UP)
        calc = Text("3² + 4² = 9 + 16 = 25 = 5²", font_size=30, color=GREEN)
        calc.shift(DOWN * 2.5)
        self.play(ReplacementTransform(intro, example_title))
        self.play(ReplacementTransform(formula, calc))
        self.wait(3)
        # Conclusion
        self.play(FadeOut(triangle), FadeOut(label_a), FadeOut(label_b), FadeOut(label_c))
        conclusion = Text("This is true for ALL right triangles!", font_size=34, color=TEAL)
        conclusion.move_to(ORIGIN)
        self.play(Write(conclusion))
        self.wait(4)

OUTPUT — return ONLY this JSON:
{
    "scene_code": "        # Full multi-scene code here (50+ lines, all indented 8 spaces)",
    "narration_script": [
        {"timestamp": 0, "duration": 5, "text": "Welcome to..."},
        {"timestamp": 5, "duration": 8, "text": "In this video..."},
        {"timestamp": 13, "duration": 12, "text": "Step 1..."},
        {"timestamp": 25, "duration": 12, "text": "Step 2..."},
        {"timestamp": 37, "duration": 10, "text": "Conclusion..."}
    ],
    "estimated_duration_seconds": 60,
    "title": "Short Title"
}

CRITICAL CHECKLIST before responding:
✓ At least 50 lines of scene_code
✓ At least 8 self.wait() calls
✓ No banned words: MathTex, Tex, import, NumberPlane, Axes, hypotenuse
✓ All code indented 8 spaces (2 levels inside construct method)"""

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
    async def enhance_prompt(self, topic: str, language: str = "en") -> str:
        """
        Step 1: Use LLM to expand a simple user prompt into a detailed
        scene-by-scene storyboard. This richer storyboard is then used
        by the Manim code generator for more accurate, longer animations.
        """
        language_instruction = "in English" if language == "en" else "in Hindi (Devanagari script)"

        enhancement_prompt = f"""You are a math education director. A user wants a video about:
"{topic}"

Write a DETAILED scene-by-scene storyboard for a 60-second educational animation. Be VERY specific — describe exactly what shapes, colors, text, and animations should appear in each scene.

Format your response as a detailed paragraph covering:
SCENE 1 - TITLE (5s): [exact title text, colors]
SCENE 2 - INTRO (8s): [what text appears, what concept is introduced]
SCENE 3 - STEP 1 (12s): [specific shapes, e.g. "draw a right triangle with legs labeled 'a' and 'b' in RED, hypotenuse 'c' in YELLOW"]
SCENE 4 - STEP 2 (12s): [next visual step, e.g. "draw three squares on each side of the triangle, label areas a², b², c²"]
SCENE 5 - STEP 3 (12s): [calculation/example, e.g. "show 3-4-5 triangle, calculate 9+16=25"]
SCENE 6 - CONCLUSION (8s): [summary text, colors]

Be extremely specific about:
- Exact text strings to display (with Unicode math symbols like ², ∫, π, ∑)
- Which Manim objects to use (Circle, Square, Rectangle, Triangle, Arrow, Line, Dot, VGroup)
- Colors (BLUE, RED, GREEN, YELLOW, WHITE, ORANGE, PURPLE, TEAL, GOLD)
- Positioning (center, top, bottom, left, right)
- Animation sequence and timing

Narration {language_instruction}. Write the storyboard now:"""

        try:
            response = await asyncio.to_thread(
                litellm.completion,
                model=self.model,
                messages=[{"role": "user", "content": enhancement_prompt}],
                temperature=0.7,
                max_tokens=2048
            )
            enhanced = response.choices[0].message.content.strip()
            print(f"📝 Enhanced prompt ({len(enhanced)} chars):\n{enhanced[:500]}...")
            return enhanced
        except Exception as e:
            print(f"⚠ Prompt enhancement failed: {e} — using original topic")
            return topic  # Fallback to original if enhancement fails

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
        
        # Step 1: Enhance the user's simple prompt into a detailed storyboard
        print(f"📝 Enhancing prompt for topic: {topic[:80]}")
        enhanced_topic = await self.enhance_prompt(topic, language)

        language_instruction = "in English" if language == "en" else "in Hindi (Devanagari script)"
        
        user_prompt = f"""Create a COMPLETE educational Manim animation based on this detailed storyboard:

{enhanced_topic}

TECHNICAL REQUIREMENTS (scene will be REJECTED if not met):
- At least 6 self.play() calls
- At least 4 self.wait() calls
- At least 40 lines of scene_code
- Use the shapes and colors described in the storyboard above
- All text uses Text() with Unicode — e.g. Text("a² + b² = c²")
- NO MathTex, NO imports, NO NumberPlane, NO Axes

Generate the full JSON now."""

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

                # --- Logging ---
                play_count = scene_code.count("self.play")
                wait_count = scene_code.count("self.wait")
                line_count = len([l for l in scene_code.split("\n") if l.strip()])
                print(f"🎬 Attempt {attempt+1}: scene_code has {line_count} lines, {play_count} self.play(), {wait_count} self.wait()")

                # Check for banned patterns — retry if found
                banned_found = self.check_banned_patterns(scene_code)
                if banned_found:
                    last_error = f"Used banned patterns: {', '.join(banned_found)}. These do not exist in Manim."
                    print(f"⚠ Attempt {attempt+1}: banned patterns found: {banned_found} — retrying")
                    continue

                # Reject scenes that are too short (generates 2-sec videos)
                if play_count < 5 or wait_count < 3:
                    last_error = f"Scene too short: only {play_count} self.play() and {wait_count} self.wait(). Need at least 5 self.play() and 3 self.wait() for a proper educational video. Generate a FULL multi-scene explanation with title, multiple steps, and conclusion."
                    print(f"⚠ Attempt {attempt+1}: scene too short ({play_count} plays, {wait_count} waits) — retrying")
                    continue

                # Check if LLM returned full class definition instead of just method body
                if "class " in scene_code and "def construct" in scene_code:
                    full_code = scene_code
                else:
                    full_code = self.CODE_TEMPLATE.format(scene_code=scene_code)

                print(f"✅ Attempt {attempt+1}: scene accepted — {line_count} lines, {play_count} plays, {wait_count} waits")

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
        
        # Use low quality by default for fast cloud rendering (480p15)
        # Users can always re-encode locally for higher quality
        flag = quality_flags.get(quality, "-ql")
        
        # Write code to temp file
        code_path = os.path.join(output_dir, "scene.py")
        with open(code_path, "w") as f:
            f.write(code)
        
        try:
            # Extract class name from code (dynamically handles LLM-generated class names)
            import re
            class_match = re.search(r'class\s+(\w+)\s*\([^)]*Scene[^)]*\)', code)
            scene_class = class_match.group(1) if class_match else "MathAnimation"
            
            # Run manim command (low quality for faster renders on cloud)
            process = await asyncio.create_subprocess_exec(
                "manim", code_path, scene_class,
                flag, "--disable_caching", "-o", "output.mp4",
                "--media_dir", output_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=output_dir
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=900  # 15 minute timeout for longer educational videos
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
                largest_size = -1
                found_path = None
                for root, dirs, files in os.walk(output_dir):
                    # Skip partial movie files directory which contains 1s clips
                    if "partial_movie_files" in root:
                        continue
                    for f in files:
                        if f.endswith(".mp4"):
                            p = os.path.join(root, f)
                            size = os.path.getsize(p)
                            if size > largest_size:
                                largest_size = size
                                found_path = p
                
                if found_path:
                    video_path = found_path
            
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
                "error": "Render timeout exceeded (15 minutes)"
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

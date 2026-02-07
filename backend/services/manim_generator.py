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
    SYSTEM_PROMPT = """You are an expert Manim animator. Generate production-ready Manim Community Edition code for mathematical animations.

RULES:
1. Use ONLY Manim Community Edition syntax (not ManimGL)
2. Generate a single Scene class called 'MathAnimation'
3. Include proper timing with self.wait() calls
4. Use varied animations: Write, FadeIn, FadeOut, Transform, Create, etc.
5. Use LaTeX for mathematical equations: MathTex("...")
6. Add visual elements: axes, graphs, shapes, arrows
7. Keep animations between 30-120 seconds total
8. Use colors from Manim's color palette: BLUE, RED, GREEN, YELLOW, WHITE, etc.
9. Add proper spacing and positioning with .next_to(), .to_edge(), .move_to()
10. INDENT code properly - all code should be inside construct() method

OUTPUT FORMAT (STRICT):
Return ONLY a JSON object with these fields:
{
    "scene_code": "        # Code lines here (indented with 8 spaces)",
    "narration_script": [
        {"timestamp": 0, "duration": 5, "text": "Narration for first part..."},
        {"timestamp": 5, "duration": 5, "text": "Narration for second part..."}
    ],
    "estimated_duration_seconds": 60,
    "title": "Animation Title"
}

IMPORTANT:
- scene_code should NOT include class definition or construct method - just the body
- Each line in scene_code must be indented with 8 spaces (for proper Python formatting)
- narration_script should sync with animations
- Keep narration conversational and educational"""

    def __init__(self, model: str = None):
        self.model = model or self.DEFAULT_MODEL
    
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
            response = await asyncio.to_thread(
                litellm.completion,
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    return {
                        "success": False,
                        "error": "Failed to parse LLM response as JSON"
                    }
            
            # Validate required fields
            required_fields = ["scene_code", "narration_script"]
            for field in required_fields:
                if field not in result:
                    return {
                        "success": False,
                        "error": f"Missing required field: {field}"
                    }
            
            # Build complete Manim code
            full_code = self.CODE_TEMPLATE.format(scene_code=result["scene_code"])
            
            return {
                "success": True,
                "manim_code": full_code,
                "narration_script": result["narration_script"],
                "estimated_duration": result.get("estimated_duration_seconds", max_duration),
                "title": result.get("title", topic),
                "model_used": self.model
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_code(self, code: str) -> Dict[str, Any]:
        """
        Validate Manim code for syntax errors.
        
        Args:
            code: Manim Python code
            
        Returns:
            Dict with success status and any errors
        """
        try:
            compile(code, "<string>", "exec")
            return {"success": True, "valid": True}
        except SyntaxError as e:
            return {
                "success": True,
                "valid": False,
                "error": f"Syntax error at line {e.lineno}: {e.msg}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
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
            # Run manim command
            process = await asyncio.create_subprocess_exec(
                "manim", code_path, "MathAnimation",
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

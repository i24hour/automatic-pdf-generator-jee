import asyncio
import os
import sys
import tempfile
import json

# Add backend dir to python path
sys.path.append("/Users/priyanshu/Desktop/Auto pdf/backend")

from dotenv import load_dotenv
load_dotenv("/Users/priyanshu/Desktop/Auto pdf/backend/.env")

from services.manim_generator import get_manim_generator
from services.tts_engine import get_tts_engine

async def test():
    generator = get_manim_generator()
    tts = get_tts_engine()
    
    prompt = "Explain the Pythagorean theorem with visual proof"
    print(f"Testing generator with prompt: {prompt}")
    
    print("\n--- GENERATING CODE ---")
    result = await generator.generate_animation(topic=prompt, language="en")
    
    if not result.get("success"):
        print("\n--- FAILED ---")
        print(result.get("error"))
        return
        
    manim_code = result["manim_code"]
    narration_script = result.get("narration_script", [])
    
    print(f"Code lines: {len(manim_code.splitlines())}")
    print(f"Narration segments: {len(narration_script)}")
    print(narration_script)
    
    work_dir = tempfile.mkdtemp(prefix="test_vid_")
    print(f"\n--- RENDERING MANIM (Low Quality) in {work_dir} ---")
    
    render_result = await generator.render_video(
        code=manim_code,
        output_dir=work_dir,
        quality="low"
    )
    
    if not render_result.get("success"):
        print("Render failed:", render_result.get("error"))
        return
        
    video_path = render_result["video_path"]
    print(f"Video rendered to: {video_path}")
    
    # Check video length with ffprobe
    proc = await asyncio.create_subprocess_shell(
        f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {video_path}",
        stdout=asyncio.subprocess.PIPE
    )
    vid_dur, _ = await proc.communicate()
    print(f"RAW VIDEO DURATION: {vid_dur.decode().strip()} seconds")
    
    print("\n--- GENERATING TTS ---")
    full_narration = " ".join([seg["text"] for seg in narration_script])
    print(f"Narration text: {full_narration[:100]}...")
    
    audio_result = await tts.generate_audio(
        text=full_narration,
        provider="edge",
        language="en"
    )
    
    if not audio_result.get("success"):
        print("Audio failed:", audio_result.get("error"))
        return
        
    audio_path = audio_result["audio_path"]
    print(f"Audio generated to: {audio_path}")
    
    proc = await asyncio.create_subprocess_shell(
        f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {audio_path}",
        stdout=asyncio.subprocess.PIPE
    )
    aud_dur, _ = await proc.communicate()
    print(f"RAW AUDIO DURATION: {aud_dur.decode().strip()} seconds")

    print("\n--- COMBINING WITH FFMPEG ---")
    final_video_path = os.path.join(work_dir, "final_output.mp4")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        final_video_path
    ]
    
    proc = await asyncio.create_subprocess_exec(
        *ffmpeg_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    
    if proc.returncode == 0:
        proc = await asyncio.create_subprocess_shell(
            f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {final_video_path}",
            stdout=asyncio.subprocess.PIPE
        )
        final_dur, _ = await proc.communicate()
        print(f"FINAL MIXED VIDEO DURATION: {final_dur.decode().strip()} seconds")
    else:
        print("FFMPEG FAILED!", stderr.decode()[:500])

if __name__ == "__main__":
    asyncio.run(test())

"""
TTS Engine - Text-to-Speech provider abstraction.
Supports multiple providers: Edge-TTS (FREE), ElevenLabs, OpenAI TTS.
"""

import os
import asyncio
import tempfile
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""
    
    @abstractmethod
    async def generate_audio(
        self, 
        text: str, 
        voice: str,
        output_path: str
    ) -> str:
        """Generate audio from text and save to output_path."""
        pass
    
    @abstractmethod
    def get_available_voices(self, language: str = "en") -> List[Dict[str, str]]:
        """Get list of available voices for a language."""
        pass


class EdgeTTSProvider(TTSProvider):
    """
    Microsoft Edge TTS - FREE neural voices.
    Uses edge-tts library.
    """
    
    # Voice mappings
    VOICES = {
        "en": [
            {"id": "en-US-AriaNeural", "name": "Aria (Female)", "gender": "female"},
            {"id": "en-US-GuyNeural", "name": "Guy (Male)", "gender": "male"},
            {"id": "en-US-JennyNeural", "name": "Jenny (Female)", "gender": "female"},
            {"id": "en-US-ChristopherNeural", "name": "Christopher (Male)", "gender": "male"},
        ],
        "hi": [
            {"id": "hi-IN-SwaraNeural", "name": "Swara (Female)", "gender": "female"},
            {"id": "hi-IN-MadhurNeural", "name": "Madhur (Male)", "gender": "male"},
        ]
    }
    
    async def generate_audio(
        self, 
        text: str, 
        voice: str = "en-US-AriaNeural",
        output_path: str = None
    ) -> str:
        """Generate audio using Edge TTS."""
        try:
            import edge_tts
        except ImportError:
            raise ImportError("edge-tts not installed. Run: pip install edge-tts")
        
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".mp3")
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        
        return output_path
    
    def get_available_voices(self, language: str = "en") -> List[Dict[str, str]]:
        """Get available Edge TTS voices."""
        return self.VOICES.get(language, self.VOICES["en"])


class ElevenLabsProvider(TTSProvider):
    """
    ElevenLabs TTS - Premium quality voices.
    Requires API key.
    """
    
    VOICES = {
        "en": [
            {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "gender": "female"},
            {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "gender": "female"},
            {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "gender": "female"},
            {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "gender": "male"},
            {"id": "VR6AewLTigWG4xSOukaG", "name": "Arnold", "gender": "male"},
        ],
        "hi": [
            {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel (Hindi)", "gender": "female"},
        ]
    }
    
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.base_url = "https://api.elevenlabs.io/v1"
    
    async def generate_audio(
        self, 
        text: str, 
        voice: str = "21m00Tcm4TlvDq8ikWAM",
        output_path: str = None
    ) -> str:
        """Generate audio using ElevenLabs API."""
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not set")
        
        import httpx
        
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".mp3")
        
        url = f"{self.base_url}/text-to-speech/{voice}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers, timeout=60.0)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(response.content)
        
        return output_path
    
    def get_available_voices(self, language: str = "en") -> List[Dict[str, str]]:
        """Get available ElevenLabs voices."""
        return self.VOICES.get(language, self.VOICES["en"])


class OpenAITTSProvider(TTSProvider):
    """
    OpenAI TTS - Good quality, reasonable pricing.
    Requires API key.
    """
    
    VOICES = {
        "en": [
            {"id": "alloy", "name": "Alloy", "gender": "neutral"},
            {"id": "echo", "name": "Echo", "gender": "male"},
            {"id": "fable", "name": "Fable", "gender": "neutral"},
            {"id": "onyx", "name": "Onyx", "gender": "male"},
            {"id": "nova", "name": "Nova", "gender": "female"},
            {"id": "shimmer", "name": "Shimmer", "gender": "female"},
        ],
        "hi": [
            {"id": "nova", "name": "Nova (Hindi)", "gender": "female"},
            {"id": "alloy", "name": "Alloy (Hindi)", "gender": "neutral"},
        ]
    }
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
    
    async def generate_audio(
        self, 
        text: str, 
        voice: str = "nova",
        output_path: str = None
    ) -> str:
        """Generate audio using OpenAI TTS."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        import httpx
        
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".mp3")
        
        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "tts-1",
            "input": text,
            "voice": voice
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers, timeout=60.0)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(response.content)
        
        return output_path
    
    def get_available_voices(self, language: str = "en") -> List[Dict[str, str]]:
        """Get available OpenAI TTS voices."""
        return self.VOICES.get(language, self.VOICES["en"])


class TTSEngine:
    """
    Main TTS Engine that manages multiple providers.
    Supports fallback between providers.
    """
    
    PROVIDERS = {
        "edge": EdgeTTSProvider,
        "elevenlabs": ElevenLabsProvider,
        "openai": OpenAITTSProvider
    }
    
    def __init__(self, default_provider: str = "edge"):
        self.default_provider = default_provider
        self._providers: Dict[str, TTSProvider] = {}
    
    def get_provider(self, name: str) -> TTSProvider:
        """Get or create a provider instance."""
        if name not in self._providers:
            if name not in self.PROVIDERS:
                raise ValueError(f"Unknown provider: {name}")
            self._providers[name] = self.PROVIDERS[name]()
        return self._providers[name]
    
    async def generate_audio(
        self,
        text: str,
        provider: str = None,
        voice: str = None,
        language: str = "en",
        output_path: str = None
    ) -> Dict[str, Any]:
        """
        Generate audio from text.
        
        Args:
            text: Text to convert to speech
            provider: TTS provider (edge, elevenlabs, openai)
            voice: Voice ID (provider-specific)
            language: Language code (en, hi)
            output_path: Output file path
            
        Returns:
            Dict with audio_path, provider used, voice used, duration
        """
        provider_name = provider or self.default_provider
        tts = self.get_provider(provider_name)
        
        # Get default voice if not specified
        if voice is None:
            voices = tts.get_available_voices(language)
            voice = voices[0]["id"] if voices else None
        
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".mp3")
        
        try:
            audio_path = await tts.generate_audio(text, voice, output_path)
            
            # Get audio duration
            duration = await self._get_audio_duration(audio_path)
            
            return {
                "success": True,
                "audio_path": audio_path,
                "provider": provider_name,
                "voice": voice,
                "duration_seconds": duration
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": provider_name
            }
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration using ffprobe."""
        try:
            process = await asyncio.create_subprocess_exec(
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            return float(stdout.decode().strip())
        except Exception:
            return 0.0
    
    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of available providers with their status."""
        providers = []
        
        for name, provider_class in self.PROVIDERS.items():
            info = {
                "id": name,
                "name": name.title(),
                "available": True
            }
            
            # Check if API key is available for premium providers
            if name == "elevenlabs":
                info["available"] = bool(os.getenv("ELEVENLABS_API_KEY"))
                info["premium"] = True
            elif name == "openai":
                info["available"] = bool(os.getenv("OPENAI_API_KEY"))
                info["premium"] = True
            else:
                info["premium"] = False
            
            providers.append(info)
        
        return providers
    
    def get_voices(self, provider: str = None, language: str = "en") -> List[Dict[str, str]]:
        """Get available voices for a provider and language."""
        provider_name = provider or self.default_provider
        tts = self.get_provider(provider_name)
        return tts.get_available_voices(language)


# Singleton instance
_tts_engine: Optional[TTSEngine] = None


def get_tts_engine() -> TTSEngine:
    """Get the global TTS engine instance."""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = TTSEngine()
    return _tts_engine


# Test function
async def test_tts():
    """Test TTS generation."""
    engine = get_tts_engine()
    
    # Test Edge TTS (free)
    result = await engine.generate_audio(
        text="Hello! This is a test of the text to speech system.",
        provider="edge",
        language="en"
    )
    
    if result["success"]:
        print(f"✓ Audio generated: {result['audio_path']}")
        print(f"  Duration: {result['duration_seconds']:.2f}s")
    else:
        print(f"✗ Failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(test_tts())

import google.generativeai as genai
import os

api_key = os.getenv("GEMINI_API_KEY", "AIzaSyBpsf3THa04Bdp1tZ80abroEm2qddf6yZU")
genai.configure(api_key=api_key)

print("Listing available Gemini models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")

import litellm
import os

litellm.set_verbose = True
model = "gemini/gemini-2.5-flash-lite"
print(f"Testing model: {model}")
try:
    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": "Hello"}],
        api_key=os.getenv("GEMINI_API_KEY", "AIzaSyBpsf3THa04Bdp1tZ80abroEm2qddf6yZU")
    )
    print("Success")
    print("Response model:", response.model)
except Exception as e:
    print(f"Error: {e}")

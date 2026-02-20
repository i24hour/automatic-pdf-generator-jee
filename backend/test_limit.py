import litellm
import os

model = "gemini/gemini-2.5-flash-lite"
prompt = "Generate 30 short facts about space and format them strictly as a JSON list. Output EXACTLY 30 facts." 
response = litellm.completion(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    api_key=os.getenv("GEMINI_API_KEY", "AIzaSyBpsf3THa04Bdp1tZ80abroEm2qddf6yZU"),
    max_tokens=8192
)
print(len(response.choices[0].message.content))
print(response.choices[0].message.content[-50:])

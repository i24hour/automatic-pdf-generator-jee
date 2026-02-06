
import os
import sys
from dotenv import load_dotenv
import litellm

# Load env vars
load_dotenv()

def test_llm_connection():
    # Check for keys
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    print(f"Gemini Key Present: {bool(gemini_key)}")
    print(f"OpenAI Key Present: {bool(openai_key)}")
    
    # Models to test
    models = ["gemini/gemini-2.0-flash-exp", "gemini/gemini-pro", "gpt-3.5-turbo"]
    
    for model in models:
        print(f"\n--- Testing Model: {model} ---")
        try:
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "Hello, answer with specific word: ORANGE"}],
                max_tokens=10
            )
            content = response.choices[0].message.content
            print(f"✅ Success! Response: {content}")
        except Exception as e:
            print(f"❌ Failed: {str(e)}")

if __name__ == "__main__":
    test_llm_connection()

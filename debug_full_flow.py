
import requests
import json
import os
from dotenv import load_dotenv

# Load env to get API URL if set, else partial default
load_dotenv()
API_URL = "http://localhost:8000"

# Mock User Data (or use auto-login if dev mode allows, but let's try standard flow)
# We need a token. If we can't get one easily securely, we might need to mock get_current_user in the backend temporarily.
# OR, we can try to hit the backend directly if we run this locally.

def debug_flow():
    print(f"🚀 Starting End-to-End Test Portal Debug on {API_URL}...")
    
    # 1. Health Check
    try:
        r = requests.get(f"{API_URL}/")
        print(f"Health Check: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"❌ Server not running at {API_URL}. Please start backend: 'cd backend && python3 main.py'")
        return

    # 2. Login (Simulate or use a known test user)
    # Since we don't have the frontend's OIDC token, we'll try to use a test token or bypass auth if possible.
    # WAIT - The user is running locally. I can temporarily disable auth in `backend/auth.py` or use a dummy token if the backend accepts dev tokens.
    # Let's assume we can't easily login via script without a GUI.
    # ALTERNATIVE: I will add a temporary "Backdoor" endpoint to `test_router.py` to create a test WITHOUT auth for debugging, 
    # OR better: I will create a unit test file `tests/test_flow_manual.py` that imports `fastapi.testclient`.
    
    pass

if __name__ == "__main__":
    debug_flow()

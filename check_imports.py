
import sys
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")

print("Checking imports...")
try:
    import litellm
    print(f"litellm version: {litellm.version if hasattr(litellm, 'version') else 'unknown'}")
except ImportError as e:
    print(f"Failed to import litellm: {e}")
    sys.exit(1)

try:
    import google.generativeai as genai
    print(f"google-generativeai imported")
except ImportError as e:
    print(f"Failed to import google.generativeai: {e}")
    sys.exit(1)

print("Checking video_router import...")
try:
    # Mocking database and auth dependencies just for import check
    sys.path.append(os.path.join(os.getcwd(), 'backend'))
    from backend.routers import video_router
    print("video_router imported successfully")
except Exception as e:
    print(f"Failed to import video_router: {e}")
    # Don't exit, just report.

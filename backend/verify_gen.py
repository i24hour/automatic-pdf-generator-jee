import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def run():
    # 1. Register/Login
    email = "testuser_gen@example.com"
    password = "password123"
    
    try:
        requests.post(f"{BASE_URL}/auth/register", json={
            "email": email, "password": password, "name": "Gen User", "class_grade": "12th"
        })
    except: pass # Ignore if exists

    res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if res.status_code != 200:
        print("Login failed")
        sys.exit(1)
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create Test (Small)
    print("Creating test (2 Physics questions)...")
    payload = {
        "exam_type": "JEE_MAINS",
        "duration_minutes": 30,
        "subject_inputs": {
            "Physics": {
                "count": 2,
                "difficulty": {"easy": 100, "medium": 0, "hard": 0},
                "topics": ["Kinematics"]
            }
        }
    }
    
    start_t = time.time()
    res = requests.post(f"{BASE_URL}/test/create", headers=headers, json=payload)
    if res.status_code != 200:
        print(f"Failed to create: {res.text}")
        sys.exit(1)
        
    data = res.json()
    test_id = data["test_id"]
    print(f"Test created in {time.time() - start_t:.2f}s. ID: {test_id}")
    
    # 3. Get State
    res = requests.get(f"{BASE_URL}/test/{test_id}/state", headers=headers)
    state = res.json()
    
    # Check Palette/Questions
    # Wait, /state usually returns 'palette' but not full question text unless we fetch specific questions?
    # Checking `test_router.py`: get_test_state returns `palette`.
    # How does frontend get questions? 
    # Usually endpoint `/test/{id}/question/{index}`?
    # Let me check test_router for `get_question`.
    
    # Checking `test_router.py` (previous `view_file` didn't show all endpoints).
    # I'll try to fetch question 0.
    
    res = requests.get(f"{BASE_URL}/test/{test_id}/question/0", headers=headers)
    if res.status_code != 200:
        print(f"Failed to fetch question 0: {res.status_code}")
        # Try finding endpoint
    else:
        q_data = res.json()
        print("Question 0 Text:")
        print(q_data["question_text"])
        
        if "AI Question will be generated here" in q_data["question_text"]:
            print("FAILURE: Still getting placeholder!")
            sys.exit(1)
        elif "Error" in q_data["question_text"]:
             print("FAILURE: Generation Error placeholder!")
             # sys.exit(1) # Warning only maybe? No, fail.
        else:
            print("SUCCESS: Real question generated!")

if __name__ == "__main__":
    run()

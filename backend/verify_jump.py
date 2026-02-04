import requests
import json
import sys
import time

BASE_URL = "http://127.0.0.1:8000"

def run():
    ts = int(time.time())
    email = f"jump_user_{ts}@example.com"
    password = "password123"
    
    # Register
    print(f"Registering {email}...")
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": email, "password": password, "name": "Jump User", "class_grade": "12th"
    })

    # Login
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if res.status_code != 200:
        print("Login failed")
        sys.exit(1)
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print("Creating test...")
    payload = {
        "exam_type": "JEE_MAINS",
        "duration_minutes": 30,
        "subject_inputs": {
            "Physics": {"count": 2, "difficulty": {"easy": 100, "medium": 0, "hard": 0}, "topics": ["Kinematics"]},
            "Chemistry": {"count": 2, "difficulty": {"easy": 100, "medium": 0, "hard": 0}, "topics": ["Atoms"]}
        }
    }
    res = requests.post(f"{BASE_URL}/test/create", headers=headers, json=payload)
    if res.status_code != 200:
        print(f"Create failed: {res.text}")
        sys.exit(1)
        
    test_id = res.json()["test_id"]
    print(f"Test ID: {test_id}")
    
    # Start test
    requests.post(f"{BASE_URL}/test/{test_id}/start", headers=headers)
    
    # Try JUMP
    print("Testing JUMP to index 2 (Chemistry)...")
    jump_payload = {
        "question_index": 0,
        "action": "JUMP",
        "jump_to_index": 2
    }
    res = requests.post(f"{BASE_URL}/test/{test_id}/action", headers=headers, json=jump_payload)
    
    if res.status_code != 200:
        print(f"JUMP failed: {res.status_code} {res.text}")
        sys.exit(1)
        
    data = res.json()
    print(f"Next Index: {data['next_question_index']}")
    
    if data['next_question_index'] == 2:
        print("SUCCESS: JUMP worked locally.")
    else:
        print(f"FAILURE: Expected 2, got {data['next_question_index']}")
        sys.exit(1)

if __name__ == "__main__":
    run()

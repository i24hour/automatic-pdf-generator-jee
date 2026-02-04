import requests
import json
import sys
import time

BASE_URL = "http://127.0.0.1:8000"

def run():
    # Helper to get unique email
    ts = int(time.time())
    email = f"count_test_{ts}@example.com"
    password = "password123"
    
    # 1. Register/Login
    print(f"Registering {email}...")
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": email, "password": password, "name": "Count Tester", "class_grade": "12th"
    })
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if res.status_code != 200:
        print("Login failed")
        sys.exit(1)
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create Test with specific counts
    # Physics: Easy=1, Medium=0, Hard=0 (Total 1)
    # Chemistry: Easy=0, Medium=1, Hard=0 (Total 1)
    print("Creating test with specific counts...")
    payload = {
        "exam_type": "JEE_MAINS",
        "duration_minutes": 30,
        "subject_inputs": {
            "Physics": {
                "count": 1, 
                "difficulty": {"easy": 1, "medium": 0, "hard": 0}, 
                "topics": ["Kinematics"]
            },
            "Chemistry": {
                "count": 1, 
                "difficulty": {"easy": 0, "medium": 1, "hard": 0}, 
                "topics": ["Atoms"]
            }
        }
    }
    
    res = requests.post(f"{BASE_URL}/test/create", headers=headers, json=payload)
    if res.status_code != 200:
        print(f"Create Failed: {res.text}")
        sys.exit(1)
        
    test_id = res.json()["test_id"]
    print(f"Test ID: {test_id}")
    
    # 3. Verify Questions
    # Fetch questions 0 and 1
    q0 = requests.get(f"{BASE_URL}/test/{test_id}/question/0", headers=headers).json()
    q1 = requests.get(f"{BASE_URL}/test/{test_id}/question/1", headers=headers).json()
    
    print(f"Q0 Subject: {q0['subject']}, Difficulty: {q0['difficulty']}")
    print(f"Q1 Subject: {q1['subject']}, Difficulty: {q1['difficulty']}")
    
    # Validation
    # Note: Question order isn't guaranteed by API but usually sequential by subject in generation logic?
    # Actually, parallel generation + gather means order matches input iteration order usually. 
    # Physics (Clean) comes before Chemistry? 
    # Let's count totals.
    
    difficulties = {
        "Physics": [],
        "Chemistry": []
    }
    
    difficulties[q0['subject']].append(q0['difficulty'])
    difficulties[q1['subject']].append(q1['difficulty'])
    
    if "Easy" in difficulties["Physics"] and "Medium" in difficulties["Chemistry"]:
        print("SUCCESS: Difficulty counts matched!")
    else:
        print(f"FAILURE: Got {difficulties}")
        sys.exit(1)

if __name__ == "__main__":
    run()

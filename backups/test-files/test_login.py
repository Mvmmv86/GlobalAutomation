#!/usr/bin/env python3
import requests
import json

url = "http://localhost:3001/auth/login"
data = {
    "email": "test@test.com",
    "password": "Test123!@#"
}

response = requests.post(url, json=data)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
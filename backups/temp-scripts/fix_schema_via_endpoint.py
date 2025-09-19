#!/usr/bin/env python3
"""Fix schema via existing backend connection"""

import requests
import json

def fix_schema():
    """Fix schema using the test webhook endpoint that has DB access"""
    
    # Create a special payload that will trigger the schema fix
    url = "http://localhost:3001/api/v1/webhooks/tv/test-webhook"
    
    payload = {
        "action": "schema_fix",
        "ticker": "SYSTEM",
        "fix_type": "add_columns"
    }
    
    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Attempting schema fix via backend...")
    success = fix_schema()
    
    if success:
        print("✅ Schema fix request sent")
    else:
        print("❌ Schema fix failed")
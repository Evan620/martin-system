#!/usr/bin/env python3
"""
Direct Vexa Bot Dispatch using requests library
This bypasses aiohttp to avoid SSL/connection issues
"""
import os
import sys
import json
import requests
from pathlib import Path

# Add parent directory to path to import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.environ.get("VEXA_API_KEY")
API_URL = os.environ.get("VEXA_API_URL", "https://api.cloud.vexa.ai")

if not API_KEY:
    print("ERROR: VEXA_API_KEY not found in .env")
    sys.exit(1)

def dispatch_bot(meeting_url: str, bot_name: str = "ECOWAS Test Bot"):
    """Dispatch Vexa bot to a meeting using requests library"""
    
    # Extract meeting ID from URL
    if "meet.google.com" in meeting_url:
        platform = "google_meet"
        native_meeting_id = meeting_url.split("/")[-1].split("?")[0]
    else:
        print(f"ERROR: Unsupported meeting platform: {meeting_url}")
        return None
    
    url = f"{API_URL}/bots"
    headers = {
        "X-API-Key": API_KEY,
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "platform": platform,
        "native_meeting_id": native_meeting_id,
        "bot_name": bot_name,
        "metadata": {
            "test": "manual_dispatch",
            "meeting_url": meeting_url
        }
    }
    
    print(f"🤖 Dispatching Vexa Bot")
    print(f"Meeting URL: {meeting_url}")
    print(f"Platform: {platform}")
    print(f"Meeting ID: {native_meeting_id}")
    print(f"Bot Name: {bot_name}")
    print(f"API Endpoint: {url}")
    print("-" * 60)
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            session_id = data.get('sessionId') or data.get('id')
            print(f"\n✅ SUCCESS! Bot dispatched to meeting.")
            print(f"Session ID: {session_id}")
            print(f"\nFull Response:")
            print(json.dumps(data, indent=2))
            print(f"\n📝 Next Steps:")
            print(f"1. Join the meeting: {meeting_url}")
            print(f"2. Look for '{bot_name}' in the waiting room")
            print(f"3. Click 'Admit' to let the bot join")
            print(f"4. Check if the bot stays in the participant list")
            return session_id
        else:
            print(f"\n❌ FAILED to dispatch bot!")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ ERROR: {e}")
        return None

if __name__ == "__main__":
    # Hardcoded meeting URL for this test
    meeting_url = "https://meet.google.com/mov-rxad-wjn"
    
    # Allow override from command line
    if len(sys.argv) > 1:
        meeting_url = sys.argv[1]
    
    bot_name = sys.argv[2] if len(sys.argv) > 2 else "ECOWAS Test Bot"
    
    dispatch_bot(meeting_url, bot_name)

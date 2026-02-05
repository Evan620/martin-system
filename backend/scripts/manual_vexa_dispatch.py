#!/usr/bin/env python3
"""
Manual Vexa Bot Dispatch Script
Dispatches Vexa bot to a specific Google Meet URL for testing.
"""
import os
import sys
import asyncio
import aiohttp
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

API_KEY = os.environ.get("VEXA_API_KEY")
API_URL = os.environ.get("VEXA_API_URL", "https://api.cloud.vexa.ai")

if not API_KEY:
    print("ERROR: VEXA_API_KEY not found in .env")
    sys.exit(1)

async def dispatch_bot(meeting_url: str, bot_name: str = "Test Bot"):
    """Dispatch Vexa bot to a meeting"""
    
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
            "test": "manual_dispatch"
        }
    }
    
    print(f"Dispatching bot to: {meeting_url}")
    print(f"Platform: {platform}")
    print(f"Meeting ID: {native_meeting_id}")
    print(f"API URL: {url}")
    print("-" * 50)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                status = response.status
                print(f"Response Status: {status}")
                
                if status in [200, 201]:
                    data = await response.json()
                    session_id = data.get('sessionId') or data.get('id')
                    print(f"✅ SUCCESS! Bot dispatched.")
                    print(f"Session ID: {session_id}")
                    print(f"\nFull Response:")
                    print(json.dumps(data, indent=2))
                    return session_id
                else:
                    text = await response.text()
                    print(f"❌ FAILED!")
                    print(f"Response: {text}")
                    return None
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manual_vexa_dispatch.py <meeting_url> [bot_name]")
        print("Example: python manual_vexa_dispatch.py https://meet.google.com/abc-defg-hij")
        sys.exit(1)
    
    meeting_url = sys.argv[1]
    bot_name = sys.argv[2] if len(sys.argv) > 2 else "Test Bot"
    
    asyncio.run(dispatch_bot(meeting_url, bot_name))

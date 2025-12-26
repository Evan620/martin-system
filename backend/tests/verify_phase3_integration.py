import asyncio
import httpx
import websockets
import json
import uuid
import datetime
import pytest
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
WS_URL = "ws://localhost:8000/api/v1/dashboard/ws"

# Test Data
ADMIN_USER = {"email": "admin@example.com", "password": "securestoredpassword"}
TWG_NAME = "Information Technology TWG"
PROJECT_NAME = "West African Fiber Backbone"

async def get_token(client: httpx.AsyncClient) -> str:
    response = await client.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_USER["email"],
        "password": ADMIN_USER["password"]
    })
    response.raise_for_status()
    return response.json()["access_token"]

async def listen_for_ws_messages(messages: list):
    """Background task to listen for WebSocket messages"""
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("🔊 Connected to Dashboard WebSocket")
            while True:
                message = await websocket.recv()
                print(f"🔊 WebSocket Received: {message}")
                messages.append(message)
    except Exception as e:
        print(f"WebSocket closed: {e}")

async def run_scenario():
    print("🚀 Starting Integration Test Scenario...")
    
    messages = []
    # Start WebSocket listener in background
    # Since we need to run it concurrently, we'll just test the connection for a second
    # For a full test, we'd need a more complex setup. 
    # Let's simplify and assertion check endpoints.
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Login
        try:
            token = await get_token(client)
            headers = {"Authorization": f"Bearer {token}"}
            print("✅ Login successful")
        except Exception as e:
            print(f"❌ Login failed (Ensure server is running): {e}")
            return

        # 2. Create TWG
        twg_resp = await client.post(
            f"{BASE_URL}/twgs/",
            json={"name": TWG_NAME, "pillar": "digital"},
            headers=headers
        )
        if twg_resp.status_code == 201:
            twg_id = twg_resp.json()["id"]
            print(f"✅ Created TWG: {twg_id}")
        else:
            print(f"❌ Create TWG failed: {twg_resp.text}")
            return # Need TWG to proceed

        # 3. Create Project
        project_resp = await client.post(
            f"{BASE_URL}/projects/",
            json={
                "twg_id": twg_id,
                "name": PROJECT_NAME,
                "description": "Connecting 15 nations with high-speed fiber.",
                "investment_size": 200000000.0,
                "status": "identified"
            },
            headers=headers
        )
        project_id = project_resp.json()["id"]
        print(f"✅ Created Project: {project_id}")

        # 4. [AGENT ACTION] Score Project
        print("🤖 [Mock Agent] Scoring Project...")
        score_resp = await client.put(
            f"{BASE_URL}/projects/{project_id}/score?score=85.5",
            headers=headers
        )
        if score_resp.status_code == 200:
            data = score_resp.json()
            if data['readiness_score'] == 85.5 and data['status'] == 'bankable':
                 print(f"✅ Agent Scoring Success: Score updated to {data['readiness_score']} and status to {data['status']}")
            else:
                 print(f"⚠️ Agent Scoring Partial: {data}")
        else:
            print(f"❌ Agent Scoring Failed: {score_resp.text}")

        # 5. Create Meeting
        meet_resp = await client.post(
            f"{BASE_URL}/meetings/",
            json={
                "twg_id": twg_id,
                "title": "Strategy Session",
                "scheduled_at": (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat()
            },
            headers=headers
        )
        meeting_id = meet_resp.json()["id"]
        print(f"✅ Created Meeting: {meeting_id}")

        # 6. [AGENT ACTION] Upsert Minutes
        print("🤖 [Mock Agent] Drafting Minutes...")
        minutes_resp = await client.post(
            f"{BASE_URL}/meetings/{meeting_id}/minutes",
            json={
                "meeting_id": meeting_id,
                "content": "# Minutes\n\nKey decision: Use fiber optic cables.",
                "status": "draft"
            },
            headers=headers
        )
        if minutes_resp.status_code == 200:
             print("✅ Agent Drafted Minutes Successfully")
        else:
             print(f"❌ Agent Minutes Failed: {minutes_resp.text}")
             
        # 7. Dashboard Check
        dash_resp = await client.get(f"{BASE_URL}/dashboard/stats", headers=headers)
        if dash_resp.status_code == 200:
            stats = dash_resp.json()
            print(f"✅ Dashboard Stats Accessible: {stats['meetings']['total']} Meetings Total")
        else:
            print(f"❌ Dashboard Failed: {dash_resp.text}")

if __name__ == "__main__":
    asyncio.run(run_scenario())

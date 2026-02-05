#!/usr/bin/env python3
"""
Test Fireflies Bot Join and Transcription

This script:
1. Creates a Google Calendar meeting with Google Meet link
2. Waits for you to join the meeting
3. Monitors if Fireflies bot joins
4. After meeting ends, checks for transcript availability
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

from app.services.calendar_service import calendar_service
from app.services.fireflies_service import fireflies_service
import time

async def create_test_meeting():
    """Create a test meeting with Google Meet link"""
    print("📅 Creating test meeting...")
    
    # Meeting starts in 2 minutes
    start_time = datetime.utcnow() + timedelta(minutes=2)
    
    event = calendar_service.create_meeting_event(
        title="Fireflies Test Meeting - ECOWAS",
        start_time=start_time,
        duration_minutes=10,
        description="Testing Fireflies bot join and transcription",
        attendees=[]
    )
    
    if not event:
        print("❌ Failed to create meeting")
        return None
    
    meet_link = event.get('hangoutLink')
    event_id = event.get('id')
    
    if not meet_link:
        print("❌ No Google Meet link generated")
        return None
    
    print(f"✅ Meeting created successfully!")
    print(f"\n📍 Meeting Details:")
    print(f"   Title: {event.get('summary')}")
    print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"   Meet Link: {meet_link}")
    print(f"   Event ID: {event_id}")
    
    return {
        'meet_link': meet_link,
        'event_id': event_id,
        'start_time': start_time,
        'title': event.get('summary')
    }

async def monitor_meeting(meeting_info):
    """Monitor the meeting and check for Fireflies bot"""
    print("\n" + "="*60)
    print("🤖 FIREFLIES BOT MONITORING")
    print("="*60)
    
    print("\n📋 Instructions:")
    print("1. Join the meeting using this link:")
    print(f"   {meeting_info['meet_link']}")
    print("\n2. Look for 'Fireflies Notetaker' or 'Fireflies.ai' in participants")
    print("3. If it appears in waiting room, admit it")
    print("4. Speak for a minute or two (test French if you want!)")
    print("5. End the meeting")
    print("\n⏳ Waiting for meeting to start...")
    
    # Wait until meeting start time
    now = datetime.utcnow()
    wait_seconds = (meeting_info['start_time'] - now).total_seconds()
    
    if wait_seconds > 0:
        print(f"   Meeting starts in {int(wait_seconds)} seconds")
        await asyncio.sleep(wait_seconds)
    
    print("\n✅ Meeting should be live now!")
    print("   Join the meeting and check if Fireflies bot appears")
    
    # Wait for meeting duration + buffer
    meeting_duration = 10 * 60  # 10 minutes
    print(f"\n⏰ Waiting {meeting_duration // 60} minutes for meeting to complete...")
    await asyncio.sleep(meeting_duration)
    
    print("\n" + "="*60)
    print("📝 CHECKING FOR TRANSCRIPT")
    print("="*60)
    
    # Wait a bit for Fireflies to process
    print("\n⏳ Waiting 2 minutes for Fireflies to process transcript...")
    await asyncio.sleep(120)
    
    # Try to find transcript by title
    print(f"\n🔍 Searching for transcript: '{meeting_info['title']}'")
    
    transcript = await fireflies_service.search_transcripts_by_title(meeting_info['title'])
    
    if transcript:
        print("\n✅ TRANSCRIPT FOUND!")
        print(f"\n📄 Transcript Details:")
        print(f"   ID: {transcript.get('id')}")
        print(f"   Title: {transcript.get('title')}")
        print(f"   Date: {transcript.get('date')}")
        print(f"   Duration: {transcript.get('duration', 0) / 60:.1f} minutes")
        print(f"   Participants: {', '.join(transcript.get('participants', []))}")
        
        # Show first few sentences
        sentences = transcript.get('transcript_text', [])
        if sentences:
            print(f"\n💬 First few sentences:")
            for i, sentence in enumerate(sentences[:5], 1):
                speaker = sentence.get('speaker_name', 'Unknown')
                text = sentence.get('text', sentence.get('raw_text', ''))
                print(f"   {i}. {speaker}: {text}")
        
        # Show summary
        summary = transcript.get('summary', {})
        if summary:
            print(f"\n📊 Summary:")
            if summary.get('keywords'):
                print(f"   Keywords: {', '.join(summary['keywords'][:10])}")
            if summary.get('action_items'):
                print(f"   Action Items: {len(summary['action_items'])}")
                for item in summary['action_items'][:3]:
                    print(f"      - {item}")
        
        print("\n" + "="*60)
        print("✅ SUCCESS! Fireflies is working correctly!")
        print("="*60)
        return True
    else:
        print("\n❌ NO TRANSCRIPT FOUND")
        print("\nPossible reasons:")
        print("1. Fireflies bot didn't join the meeting")
        print("2. Meeting was too short (needs at least 1-2 minutes of speech)")
        print("3. Fireflies is still processing (try running test_fireflies.py in 5 min)")
        print("4. Google Workspace settings are blocking the bot")
        
        print("\n🔍 Checking recent transcripts...")
        recent = await fireflies_service.list_transcripts(limit=5)
        if recent:
            print(f"\nFound {len(recent)} recent transcripts:")
            for t in recent:
                print(f"   - {t.get('title')} ({t.get('date')})")
        
        print("\n" + "="*60)
        print("⚠️  TEST INCOMPLETE - Check Fireflies dashboard")
        print("="*60)
        return False

async def main():
    """Main test flow"""
    print("🔥 FIREFLIES BOT JOIN & TRANSCRIPTION TEST")
    print("="*60)
    
    # Check if Fireflies is configured
    if not fireflies_service.api_key:
        print("❌ ERROR: FIREFLIES_API_KEY not set in .env")
        return
    
    print(f"✓ Fireflies API Key configured")
    print(f"✓ API URL: {fireflies_service.api_url}\n")
    
    # Create test meeting
    meeting_info = await create_test_meeting()
    
    if not meeting_info:
        print("❌ Failed to create test meeting")
        return
    
    # Monitor meeting and check transcript
    success = await monitor_meeting(meeting_info)
    
    if success:
        print("\n🎉 All tests passed! Fireflies integration is working!")
    else:
        print("\n⚠️  Please check Fireflies dashboard and Google Workspace settings")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

#!/usr/bin/env python3
"""
Test Fireflies.ai API Connection

This script tests the Fireflies API connection and lists recent transcripts.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

from app.services.fireflies_service import fireflies_service

async def test_fireflies():
    """Test Fireflies API connection"""
    print("🔥 Testing Fireflies.ai API Connection")
    print("=" * 60)
    
    # Check API key
    if not fireflies_service.api_key:
        print("❌ ERROR: FIREFLIES_API_KEY not set in .env")
        return
    
    print(f"✓ API Key: {fireflies_service.api_key[:20]}...")
    print(f"✓ API URL: {fireflies_service.api_url}")
    print()
    
    # Test 1: List recent transcripts
    print("📋 Fetching recent transcripts...")
    print("-" * 60)
    
    transcripts = await fireflies_service.list_transcripts(limit=5)
    
    if transcripts:
        print(f"✅ Found {len(transcripts)} transcripts:\n")
        for i, transcript in enumerate(transcripts, 1):
            print(f"{i}. {transcript.get('title', 'Untitled')}")
            print(f"   ID: {transcript.get('id')}")
            print(f"   Date: {transcript.get('date')}")
            print(f"   Duration: {transcript.get('duration', 0) / 60:.1f} minutes")
            print(f"   Participants: {', '.join(transcript.get('participants', []))}")
            print()
        
        # Test 2: Fetch full transcript for first one
        if transcripts:
            first_id = transcripts[0].get('id')
            print(f"\n📄 Fetching full transcript for: {transcripts[0].get('title')}")
            print("-" * 60)
            
            full_transcript = await fireflies_service.get_transcript(first_id)
            
            if full_transcript:
                print("✅ Successfully retrieved full transcript!")
                print(f"\nTitle: {full_transcript.get('title')}")
                print(f"Participants: {', '.join(full_transcript.get('participants', []))}")
                
                # Show first few sentences
                sentences = full_transcript.get('transcript_text', [])
                if sentences:
                    print(f"\nFirst 3 sentences:")
                    for sentence in sentences[:3]:
                        speaker = sentence.get('speaker_name', 'Unknown')
                        text = sentence.get('text', sentence.get('raw_text', ''))
                        print(f"  {speaker}: {text}")
                
                # Show summary if available
                summary = full_transcript.get('summary', {})
                if summary:
                    print(f"\n📊 Summary:")
                    if summary.get('keywords'):
                        print(f"  Keywords: {', '.join(summary['keywords'][:5])}")
                    if summary.get('action_items'):
                        print(f"  Action Items: {len(summary['action_items'])}")
            else:
                print("❌ Failed to retrieve full transcript")
    else:
        print("⚠️  No transcripts found. This could mean:")
        print("   1. You haven't had any meetings with Fireflies bot yet")
        print("   2. Fireflies hasn't finished processing recent meetings")
        print("   3. There's an API authentication issue")
        print("\n💡 Next steps:")
        print("   1. Create a test meeting in Google Calendar")
        print("   2. Make sure Fireflies is connected to your calendar")
        print("   3. Join the meeting and verify Fireflies bot joins")
        print("   4. Wait for Fireflies to process the transcript (~5-10 min)")
        print("   5. Run this script again")

if __name__ == "__main__":
    asyncio.run(test_fireflies())

import asyncio
import sys
import os
import logging
from loguru import logger

# Add backend to path
sys.path.append(os.getcwd())

from app.services.fireflies_service import fireflies_service

# Configure logging to see the warnings we added
logging.basicConfig(level=logging.INFO)
logger.remove()
logger.add(sys.stdout, level="INFO")

async def test_fetch_partial():
    # ID from the user's logs
    transcript_id = "01KGPWC0AXKE1FHBTA1AZMPVBX"
    
    logger.info(f"Testing fetch for transcript: {transcript_id}")
    logger.info("Expectation: Should see warnings about GraphQL errors, but still return data.")
    
    transcript = await fireflies_service.get_transcript(transcript_id)
    
    if transcript:
        logger.info("✅ SUCCESS! Transcript data returned.")
        logger.info(f"Title: {transcript.get('title')}")
        
        sentences = transcript.get('transcript_text', [])
        logger.info(f"Sentences found: {len(sentences)}")
        
        if len(sentences) > 0:
            logger.info(f"First sentence: {sentences[0].get('text')}")
            
        logger.info(f"Video URL: {transcript.get('video_url')}")
        logger.info(f"Audio URL: {transcript.get('audio_url')}")
        
        if transcript.get('video_url') is None:
             logger.info("Note: Video URL is None as expected (Plan Limit)")
    else:
        logger.error("❌ FAILURE: No data returned.")

if __name__ == "__main__":
    asyncio.run(test_fetch_partial())

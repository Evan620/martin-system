
import os
import sys
import asyncio
import aiohttp
import logging
from dotenv import load_dotenv

# Load env vars
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vexa_debug")

API_KEY = os.environ.get("VEXA_API_KEY")
API_URL = os.environ.get("VEXA_API_URL", "https://api.cloud.vexa.ai")  # Match config.py default

if not API_KEY:
    logger.error("VEXA_API_KEY not found in .env")
    sys.exit(1)

async def check_transcript(platform, native_id):
    url = f"{API_URL}/transcripts/{platform}/{native_id}"
    logger.info(f"Querying: {url}")
    
    headers = {
        "X-API-Key": API_KEY,
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as resp:
                logger.info(f"Status Code: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get('status', 'unknown')
                    logger.info(f"Vexa Status: {status}")
                    logger.info("--- Payload Summary ---")
                    logger.info(f"ID: {data.get('id')}")
                    logger.info(f"Text Length: {len(data.get('text', ''))}")
                    logger.info(f"Segments: {len(data.get('segments', []))}")
                    logger.info(f"Created: {data.get('created_at')}")
                    # Dump full response for inspection if needed
                    # print(data)
                else:
                    text = await resp.text()
                    logger.error(f"Error Response: {text}")
        except Exception as e:
            logger.error(f"Request failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python debug_vexa_transcript.py <platform> <native_meeting_id>")
        print("Example: python debug_vexa_transcript.py google_meet efv-evrf-cxi")
        
        # Default to a known recent ID from logs for convenience if user runs without args
        print("\nRunning default test case from logs: google_meet efv-evrf-cxi")
        asyncio.run(check_transcript("google_meet", "efv-evrf-cxi"))
    else:
        asyncio.run(check_transcript(sys.argv[1], sys.argv[2]))

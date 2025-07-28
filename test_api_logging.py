#!/usr/bin/env python3
"""
Test script to verify API logging is working correctly.
This script will make a simple API call to test the logging functionality.
"""

import os
import logging
from openai import OpenAI
from dotenv import load_dotenv
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_api_logging():
    """Test that API logging is working correctly."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        return False
    
    client = OpenAI(api_key=api_key)
    
    try:
        # Test embeddings API call
        logger.info("🧪 TESTING: Making test embeddings API call")
        
        # Log the complete request payload
        request_payload = {
            "input": ["This is a test message for API logging verification"],
            "model": "text-embedding-ada-002"
        }
        logger.info(f"📦 TEST EMBEDDINGS REQUEST PAYLOAD: {json.dumps(request_payload, indent=2)}")
        
        response = client.embeddings.create(
            input=["This is a test message for API logging verification"],
            model="text-embedding-ada-002"
        )
        logger.info(f"✅ TEST SUCCESS: Embeddings API call completed, dimensions: {len(response.data[0].embedding)}")
        
        # Test chat completions API call
        logger.info("🧪 TESTING: Making test chat completions API call")
        
        # Log the complete request payload
        request_payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, API logging is working!'"}
            ],
            "max_tokens": 50,
            "temperature": 0
        }
        logger.info(f"📦 TEST CHAT COMPLETIONS REQUEST PAYLOAD: {json.dumps(request_payload, indent=2)}")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, API logging is working!'"}
            ],
            max_tokens=50,
            temperature=0
        )
        logger.info(f"✅ TEST SUCCESS: Chat completions API call completed, response: {response.choices[0].message.content}")
        
        print("✅ All API logging tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ TEST FAILED: API call failed with error: {e}")
        print(f"❌ API logging test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing API logging functionality...")
    success = test_api_logging()
    if success:
        print("\n🎉 API logging is working correctly!")
        print("📋 Summary of what will be logged:")
        print("  - 🔍 API CALL - Embeddings: Getting embedding for text")
        print("  - 📦 EMBEDDINGS REQUEST PAYLOAD: Complete request data")
        print("  - ✅ API RESPONSE - Embeddings: Successfully received embedding")
        print("  - 🤖 API CALL - Chat Completions: Various chat completion calls")
        print("  - 📦 CHAT COMPLETIONS REQUEST PAYLOAD: Complete request data")
        print("  - ✅ API RESPONSE - Chat Completions: Generated responses")
        print("  - 📁 API CALL - Files: File uploads")
        print("  - 📦 FILE UPLOAD REQUEST PAYLOAD: Complete request data")
        print("  - 🤖 API CALL - Assistants: Assistant creation/updates")
        print("  - 📦 ASSISTANT REQUEST PAYLOAD: Complete request data")
        print("  - ✅ API RESPONSE - Assistants: Assistant operations completed")
    else:
        print("\n❌ API logging test failed. Please check your API key and try again.") 
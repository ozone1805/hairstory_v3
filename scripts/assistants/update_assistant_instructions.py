import os
import sys
import logging
from openai import OpenAI
from dotenv import load_dotenv
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ASSISTANT_ID = os.getenv('ASSISTANT_ID')

if not OPENAI_API_KEY or not ASSISTANT_ID:
    print("Error: OPENAI_API_KEY and ASSISTANT_ID must be set in the .env file.")
    sys.exit(1)

if len(sys.argv) != 2:
    print(f"Usage: python {sys.argv[0]} <instructions_file.txt>")
    sys.exit(1)

instructions_file = sys.argv[1]

try:
    with open(instructions_file, 'r', encoding='utf-8') as f:
        new_instructions = f.read()
except Exception as e:
    print(f"Error reading instructions file: {e}")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

try:
    logger.info(f"🤖 API CALL - Assistants: Updating assistant {ASSISTANT_ID} with new instructions")
    logger.info(f"📝 Instructions Length: {len(new_instructions)} characters")
    
    # Log the complete request payload
    request_payload = {
        "assistant_id": ASSISTANT_ID,
        "instructions": new_instructions
    }
    logger.info(f"📦 ASSISTANT UPDATE REQUEST PAYLOAD: {json.dumps(request_payload, indent=2)}")
    
    updated_assistant = client.beta.assistants.update(
        assistant_id=ASSISTANT_ID,
        instructions=new_instructions
    )
    
    logger.info(f"✅ API RESPONSE - Assistants: Successfully updated assistant {ASSISTANT_ID}")
    print(f"Successfully updated assistant instructions. Assistant ID: {ASSISTANT_ID}")
except Exception as e:
    logger.error(f"❌ API ERROR - Assistants: Failed to update assistant {ASSISTANT_ID}: {e}")
    print(f"Error updating assistant: {e}")
    sys.exit(1) 
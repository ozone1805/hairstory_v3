import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

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
    updated_assistant = client.beta.assistants.update(
        assistant_id=ASSISTANT_ID,
        instructions=new_instructions
    )
    print(f"Successfully updated assistant instructions. Assistant ID: {ASSISTANT_ID}")
except Exception as e:
    print(f"Error updating assistant: {e}")
    sys.exit(1) 
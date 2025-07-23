import os
import openai
import requests
import time
import sys

# Constants
API_BASE_URL = "https://api.openai.com/v1"
FILE_PATH = "product_catalogue.txt"
ASSISTANT_NAME = "Hairstory demo v10"
VECTOR_STORE_NAME = "Hairstory Product Catalog"
MAX_RETRIES = 30
POLL_INTERVAL = 2

def load_api_key():
    """Load and validate OpenAI API key from environment."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment variables.")
    return api_key

def get_headers(api_key):
    """Get headers for API requests."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v2"
    }

def upload_file(api_key):
    """Upload the catalog file and return file ID."""
    print("Uploading file...")
    openai.api_key = api_key
    
    uploaded_file = openai.files.create(
        file=open(FILE_PATH, "rb"),
        purpose="assistants"
    )
    file_id = uploaded_file.id
    print(f"✅ Uploaded {FILE_PATH} — File ID: {file_id}")
    return file_id

def create_vector_store(api_key, headers):
    """Create a vector store and return its ID."""
    print("Creating vector store...")
    
    vector_store_data = {
        "name": VECTOR_STORE_NAME,
        "expires_after": {
            "anchor": "last_active_at",
            "days": 30
        }
    }
    
    response = requests.post(
        f"{API_BASE_URL}/vector_stores",
        headers=headers,
        json=vector_store_data
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create vector store: {response.status_code} - {response.text}")
        sys.exit(1)
    
    vector_store = response.json()
    vector_store_id = vector_store["id"]
    print(f"✅ Vector store created — ID: {vector_store_id}")
    return vector_store_id

def add_file_to_vector_store(api_key, headers, vector_store_id, file_id):
    """Add file to vector store and return batch ID."""
    print("Adding file to vector store...")
    
    file_batch_data = {"file_ids": [file_id]}
    
    response = requests.post(
        f"{API_BASE_URL}/vector_stores/{vector_store_id}/file_batches",
        headers=headers,
        json=file_batch_data
    )
    
    if response.status_code not in (200, 202):
        print(f"❌ Failed to add file to vector store: {response.status_code} - {response.text}")
        sys.exit(1)
    
    file_batch = response.json()
    file_batch_id = file_batch["id"]
    print(f"✅ File batch created — ID: {file_batch_id}")
    return file_batch_id

def wait_for_batch_completion(api_key, headers, vector_store_id, file_batch_id):
    """Wait for file batch to complete processing."""
    print("Waiting for file batch to complete...")
    
    for attempt in range(MAX_RETRIES):
        response = requests.get(
            f"{API_BASE_URL}/vector_stores/{vector_store_id}/file_batches/{file_batch_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to check file batch status: {response.status_code} - {response.text}")
            sys.exit(1)
        
        batch_status = response.json()
        status = batch_status["status"]
        
        if status == "completed":
            print("✅ File batch completed successfully")
            return
        elif status == "failed":
            error_msg = batch_status.get('error', 'Unknown error')
            print(f"❌ File batch failed: {error_msg}")
            sys.exit(1)
        else:
            print(f"⏳ File batch status: {status} (attempt {attempt + 1}/{MAX_RETRIES})")
            time.sleep(POLL_INTERVAL)
    
    print(f"❌ File batch did not complete within {MAX_RETRIES * POLL_INTERVAL} seconds")
    sys.exit(1)

def create_assistant(api_key, vector_store_id):
    """
    Create assistant with vector store for file search.
    
    Args:
        api_key (str): OpenAI API key
        vector_store_id (str): ID of the vector store
        
    Returns:
        str: Assistant ID
    """
    print("Creating assistant...")
    openai.api_key = api_key
    
    assistant = openai.beta.assistants.create(
        name=ASSISTANT_NAME,
        instructions="""You are a warm, understanding haircare assistant. Your goal is to get to know the user’s hair and lifestyle through a natural conversation.
Be curious and kind — you’re not administering a quiz, you’re having a dialogue to help them feel heard and supported.
I want to be very clear, you only recommend products from the uploaded hairstory product catalog, nothing else.
When reffering to products, use the name field in the product catalog to recommend products. Use the url field to link to the product.
When recommending products, only use products labeled singleton in the type field. If all products haoppen to be in a bundle, recommend the bundle.

Ask questions organically, weaving them into the flow of conversation. Over time, you’ll want to learn things like:
- How they would describe their hair (texture, thickness, density)
- What their hair type is (oily, dry, normal, combination, etc.)
- Any concerns they have or things they’d like to change
- What a good hair day feels like for them
- How often they wash their hair
- Whether they color treat it
- If they use shampoo and conditioner
- How long their hair is
- How they typically style it and what products they use

You don’t need to ask these all at once. Take your time and build trust, but don't ask too many questions at once or in general.
Once you have enough information, recommend a personalized haircare routine using only items from the uploaded hairstory product catalog.
This can include one or more product bundles suited to their hair type, concerns, and lifestyle.

Always be thoughtful and never assume.
Let the user guide the tone.
Your goal is to help them feel confident in their routine."""
,
        model="gpt-4o-mini",
        tools=[{"type": "file_search"}],
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store_id]
            }
        }
    )
    assistant_id = assistant.id
    print(f"✅ Assistant created — ID: {assistant_id}")
    return assistant_id

def print_summary(assistant_id, file_id, vector_store_id, file_batch_id):
    """Print summary of created resources."""
    print(f"\n📋 Summary:")
    print(f"Assistant ID: {assistant_id}")
    print(f"File ID: {file_id}")
    print(f"Vector Store ID: {vector_store_id}")
    print(f"File Batch ID: {file_batch_id}")
    print(f"🌐 Playground URL: https://platform.openai.com/playground/assistants?assistant={assistant_id}&mode=assistant")

def main():
    """Main function to orchestrate the assistant creation process."""
    try:
        # Load API key
        api_key = load_api_key()
        headers = get_headers(api_key)
        
        # Step 1: Upload file
        file_id = upload_file(api_key)
        
        # Step 2: Create vector store
        vector_store_id = create_vector_store(api_key, headers)
        
        # Step 3: Add file to vector store
        file_batch_id = add_file_to_vector_store(api_key, headers, vector_store_id, file_id)
        
        # Step 4: Wait for batch completion
        wait_for_batch_completion(api_key, headers, vector_store_id, file_batch_id)
        
        # Step 5: Create assistant
        assistant_id = create_assistant(api_key, vector_store_id)
        
        # Step 6: Print summary
        print_summary(assistant_id, file_id, vector_store_id, file_batch_id)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

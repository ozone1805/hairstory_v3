import os
import openai
from pinecone import Pinecone
import json
from typing import Optional, Dict

# Load environment variables
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not PINECONE_API_KEY or not PINECONE_ENV or not OPENAI_API_KEY:
    raise ValueError("PINECONE_API_KEY, PINECONE_ENV, and OPENAI_API_KEY must be set as environment variables.")

# Initialize clients
client = openai.OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("hairstory-products")

# Define a user profile to collect structured data
user_profile: Dict[str, Optional[str]] = {
    "hair_type": None,        # e.g., straight, wavy, curly, coily
    "oiliness": None,         # e.g., oily, dry, normal, combination
    "length": None,           # e.g., short, medium, long
    "concerns": None,         # e.g., breakage, volume, color-treated, etc.
    "frizziness": None,       # e.g., low, medium, high
    "curls": None             # e.g., none, loose, tight, coily, etc.
}

# List of fields and friendly prompts
profile_fields = [
    ("hair_type", "How would you describe your hair type? (e.g., straight, wavy, curly, coily)"),
    ("oiliness", "Is your scalp or hair oily, dry, normal, or a combination?"),
    ("length", "How long is your hair? (short, medium, long)"),
    ("concerns", "Do you have any hair concerns or goals? (e.g., breakage, volume, color-treated, etc.)"),
    ("frizziness", "How would you rate your hair's frizziness? (low, medium, high)"),
    ("curls", "How would you describe your curls? (none, loose, tight, coily, etc.)")
]

def is_profile_complete(profile):
    return all(profile[field] for field, _ in profile_fields)

def profile_to_string(profile):
    return ", ".join(f"{field.replace('_', ' ').capitalize()}: {profile[field]}" for field, _ in profile_fields)

def print_profile(profile):
    print("\n📝 Your Hair Profile:")
    for field, _ in profile_fields:
        value = profile[field]
        print(f"  {field.replace('_', ' ').capitalize()}: {value}")
    print()

def get_embedding(text):
    """Get embedding for text using OpenAI."""
    response = client.embeddings.create(
        input=[text],
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def query_pinecone(user_input, top_k=5):
    """Query Pinecone for similar products."""
    # Get embedding for user input
    query_embedding = get_embedding(user_input)
    
    # Query Pinecone
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )
    
    return results.matches

def format_products_for_prompt(products):
    """Format retrieved products for the prompt."""
    formatted_products = []
    for product in products:
        formatted_products.append({
            "name": product.metadata.get("name", ""),
            "subtitle": product.metadata.get("subtitle", ""),
            "url": product.metadata.get("url", ""),
            "type": product.metadata.get("type", ""),
            "similarity_score": product.score
        })
    return formatted_products

def create_recommendation_prompt(user_input, products):
    """Create a prompt for the OpenAI API with user input and relevant products."""
    
    products_text = ""
    for i, product in enumerate(products, 1):
        products_text += f"""
{i}. {product['name']}
   - {product['subtitle']}
   - Type: {product['type']}
   - URL: {product['url']}
   - Relevance Score: {product['similarity_score']:.3f}
"""
    
    prompt = f"""You are a warm, understanding haircare assistant for Hairstory. Your goal is to help users find the perfect haircare routine based on their needs.

USER'S INPUT: {user_input}

RELEVANT HAIRSTORY PRODUCTS (ranked by relevance):
{products_text}

INSTRUCTIONS:
1. Analyze the user's hair type, concerns, and needs from their input
2. Recommend specific products from the list above that would work best for them
3. Explain why these products are a good match for their hair type/concerns
4. Be warm, supportive, and educational
5. Only recommend products from the Hairstory catalog above
6. Include the product URLs when recommending products
7. If no products seem relevant, ask clarifying questions about their hair type and concerns

Please provide a personalized recommendation:"""

    return prompt

# Add a function to generate the next conversational question using OpenAI

def generate_next_question(profile, conversation_history):
    missing_fields = [field for field, _ in profile_fields if not profile[field]]
    if not missing_fields:
        return None
    # Compose a prompt for the AI
    profile_summary = profile_to_string(profile)
    last_user_message = conversation_history[-1]["content"] if conversation_history else ""
    prompt = (
        f"You are a warm, friendly haircare assistant. You are building a hair profile for the user. "
        f"Here is the information you have so far: {profile_summary}. "
        f"The last thing the user said was: '{last_user_message}'. "
        f"Please ask a conversational, context-aware question to learn about the user's {missing_fields[0].replace('_', ' ')}. "
        f"Be friendly and natural. Only ask about one missing field at a time."
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a warm, friendly haircare assistant. You are building a hair profile for the user."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100,
        temperature=0.7
    )
    ai_content = response.choices[0].message.content
    return ai_content.strip() if ai_content else ""

def chat_with_user():
    """Main chat function."""
    print("🌟 Welcome to Hairstory Haircare Assistant! 🌟")
    print("Let's get to know your hair so I can help you find the perfect products.")
    print("Type 'quit' to exit.\n")

    global user_profile
    conversation_history = []
    while True:
        # Ask for missing fields using AI
        while not is_profile_complete(user_profile):
            ai_question = generate_next_question(user_profile, conversation_history)
            if not ai_question:
                break
            retry = False
            for attempt in range(2):  # Try up to 2 times
                user_input = input(f"{ai_question}\nYou: ").strip()
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("Thank you for using Hairstory Haircare Assistant! 💫")
                    return
                conversation_history.append({"role": "user", "content": user_input})
                missing_fields = [field for field, _ in profile_fields if not user_profile[field]]
                if missing_fields:
                    extract_prompt = (
                        f"Given the user's answer: '{user_input}', "
                        f"what is their {missing_fields[0].replace('_', ' ')}? "
                        f"Respond with only the value, no extra words. If unclear, respond with 'unknown'."
                    )
                    extract_response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Extract structured hair profile data from user answers."},
                            {"role": "user", "content": extract_prompt}
                        ],
                        max_tokens=20,
                        temperature=0
                    )
                    value = extract_response.choices[0].message.content
                    value = value.strip() if value else ""
                    if value.lower() != 'unknown' and value != "":
                        user_profile[missing_fields[0]] = value
                        break  # Success, move to next question
                    else:
                        if attempt == 0:
                            print("Sorry, I couldn't understand your answer. Let's try again.")
                        else:
                            print("Sorry, I couldn't parse that. Let's move on.")
        # If profile is complete, proceed
        if is_profile_complete(user_profile):
            print("\n🔍 Finding the perfect products for you based on your hair profile...")
            try:
                profile_text = profile_to_string(user_profile)
                similar_products = query_pinecone(profile_text, top_k=5)
                if not similar_products:
                    print("I couldn't find any relevant products. Could you clarify your hair profile?")
                    user_profile[profile_fields[0][0]] = None
                    continue
                formatted_products = format_products_for_prompt(similar_products)
                prompt = create_recommendation_prompt(profile_text, formatted_products)
                print_profile(user_profile)
                print("💭 Generating personalized recommendation...")
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a warm, knowledgeable haircare assistant for Hairstory. You help users find the perfect haircare routine based on their hair type and concerns."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                recommendation = response.choices[0].message.content
                print("\n💡 Hairstory Assistant:")
                print(recommendation)
                print("\n" + "="*50 + "\n")
                next_action = input("Would you like to update your hair profile or quit? (update/quit): ").strip().lower()
                if next_action == "quit":
                    print("Thank you for using Hairstory Haircare Assistant! 💫")
                    break
                elif next_action == "update":
                    print("Which aspect would you like to update?")
                    for idx, (field, prompt) in enumerate(profile_fields, 1):
                        print(f"{idx}. {field.replace('_', ' ').capitalize()} (current: {user_profile[field]})")
                    try:
                        field_idx = int(input("Enter the number of the field to update: ")) - 1
                        if 0 <= field_idx < len(profile_fields):
                            user_profile[profile_fields[field_idx][0]] = None
                        else:
                            print("Invalid selection. Returning to main menu.")
                    except ValueError:
                        print("Invalid input. Returning to main menu.")
                else:
                    print("Okay! If you want to update your profile, just type 'update' at any prompt.")
            except Exception as e:
                print(f"❌ Sorry, I encountered an error: {str(e)}")
                print("Please try again or rephrase your answer.\n")
                user_profile[profile_fields[0][0]] = None
        else:
            print("Let's continue building your hair profile.")

if __name__ == "__main__":
    chat_with_user() 
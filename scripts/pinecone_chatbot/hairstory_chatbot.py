import os
import openai
from pinecone import Pinecone
import json
from typing import Optional, Dict
from dotenv import load_dotenv
load_dotenv()

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
# Remove hardcoded user_profile initialization
# user_profile: Dict[str, Optional[str]] = {
#     "hair_type": None,        # e.g., straight, wavy, curly, coily
#     "oiliness": None,         # e.g., oily, dry, normal, combination
#     "length": None,           # e.g., short, medium, long
#     "concerns": None,         # e.g., breakage, volume, color-treated, etc.
#     "frizziness": None,       # e.g., low, medium, high
#     "curls": None             # e.g., none, loose, tight, coily, etc.
# }

# List of fields and friendly prompts
profile_fields = [
    ("hair_type", "How would you describe your hair type? (e.g., straight, wavy, curly, coily)"),
    ("oiliness", "Is your scalp or hair oily, dry, normal, or a combination?"),
    ("length", "How long is your hair? (short, medium, long)"),
    ("concerns", "Do you have any hair concerns or goals? (e.g., breakage, volume, color-treated, etc.)"),
    ("frizziness", "How would you rate your hair's frizziness? (low, medium, high)"),
    ("curls", "How would you describe your curls? (none, loose, tight, coily, etc.)")
]

def map_user_input_to_field_value(field, user_input):
    """Map natural language user input to valid field values."""
    text = user_input.strip().lower()
    if field == "hair_type":
        if any(word in text for word in ["straight", "no curl", "no wave"]):
            return "straight"
        if any(word in text for word in ["wavy", "wave", "loose wave"]):
            return "wavy"
        if any(word in text for word in ["curly", "curl", "ringlet"]):
            return "curly"
        if any(word in text for word in ["coily", "kinky", "tight curl"]):
            return "coily"
    elif field == "oiliness":
        if any(word in text for word in ["oily", "greasy", "need to wash often"]):
            return "oily"
        if any(word in text for word in ["dry", "flaky", "parched"]):
            return "dry"
        if any(word in text for word in ["normal", "balanced", "average"]):
            return "normal"
        if any(word in text for word in ["combination", "mixed"]):
            return "combination"
    elif field == "length":
        if any(word in text for word in ["short", "pixie", "bob"]):
            return "short"
        if any(word in text for word in ["medium", "shoulder", "mid-length", "mid length"]):
            return "medium"
        if any(word in text for word in ["long", "waist", "chest", "below shoulder"]):
            return "long"
    elif field == "concerns":
        if any(word in text for word in ["none", "no concerns", "no issues"]):
            return "none"
        if any(word in text for word in ["breakage", "split ends"]):
            return "breakage"
        if any(word in text for word in ["volume", "flat"]):
            return "volume"
        if any(word in text for word in ["color", "color-treated", "dye", "colored", "no color"]):
            return "color-treated"
        if any(word in text for word in ["frizz", "frizzy"]):
            return "frizziness"
        if any(word in text for word in ["thinning", "hair loss"]):
            return "thinning"
    elif field == "frizziness":
        if any(word in text for word in ["low", "not frizzy", "smooth"]):
            return "low"
        if any(word in text for word in ["medium", "sometimes frizzy"]):
            return "medium"
        if any(word in text for word in ["high", "very frizzy", "always frizzy"]):
            return "high"
    elif field == "curls":
        if any(word in text for word in ["none", "no curls", "straight", "natural", "relaxed"]):
            return "none"
        if any(word in text for word in ["loose", "wavy", "waves"]):
            return "loose"
        if any(word in text for word in ["tight", "kinky"]):
            return "tight"
        if "coily" in text:
            return "coily"
    return None

def is_profile_complete(profile):
    # If profile is empty, it's not complete
    if not profile:
        return False
    return all(profile.get(field) for field, _ in profile_fields)

def profile_to_string(profile):
    return ", ".join(f"{field.replace('_', ' ').capitalize()}: {profile.get(field, 'Not provided')}" for field, _ in profile_fields)

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
    missing_fields = [field for field, _ in profile_fields if not profile.get(field)]
    if not missing_fields:
        return None
    # Compose a prompt for the AI
    profile_summary = profile_to_string(profile)
    last_user_message = conversation_history[-1]["content"] if conversation_history else ""
    profile_field_names = [field for field, _ in profile_fields]
    fields_str = ", ".join(profile_field_names)
    prompt = (
        f"You are a warm, friendly haircare assistant. You are building a hair profile for the user. "
        f"Here is the information you have so far: {profile_summary}. "
        f"The last thing the user said was: '{last_user_message}'. "
        f"Please ask a conversational, context-aware question to learn about the user's {missing_fields[0].replace('_', ' ')}. "
        f"Only ask about these fields, one at a time: {fields_str}. "
        f"Be friendly and natural."
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

def build_profile_with_function_call(conversation_history):
    """Use OpenAI function calling to extract as much of the hair profile as possible from the conversation."""
    function_schema = [
        {
            "name": "build_hair_profile",
            "description": "Extracts a complete hair profile from the user's conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hair_type": {"type": "string", "description": "e.g., straight, wavy, curly, coily"},
                    "oiliness": {"type": "string", "description": "e.g., oily, dry, normal, combination"},
                    "length": {"type": "string", "description": "e.g., short, medium, long"},
                    "concerns": {"type": "string", "description": "e.g., breakage, volume, color-treated, etc."},
                    "frizziness": {"type": "string", "description": "e.g., low, medium, high"},
                    "curls": {"type": "string", "description": "e.g., none, loose, tight, coily, etc."}
                },
                "required": []
            }
        }
    ]
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=conversation_history,
        functions=function_schema,
        function_call={"name": "build_hair_profile"},
        max_tokens=300,
        temperature=0
    )
    choice = response.choices[0]
    if choice.finish_reason == "function_call":
        args = json.loads(choice.message.function_call.arguments)
        return args
    return {}

def chat_with_user():
    """Main chat function."""
    print("\U0001F31F Welcome to Hairstory Haircare Assistant! \U0001F31F")
    print("Let's get to know your hair so I can help you find the perfect products.")
    print("Type 'quit' to exit.\n")

    global user_profile
    user_profile = {}  # Dynamic initialization
    conversation_history = []
    while True:
        # Build profile using function calling after each user input
        while not is_profile_complete(user_profile):
            # Find missing fields
            missing_fields = [field for field, _ in profile_fields if not user_profile.get(field)]
            if not missing_fields:
                break
            # Ask about the next missing field
            ai_question = generate_next_question(user_profile, conversation_history)
            if not ai_question:
                break
            user_input = input(f"{ai_question}\nYou: ").strip()
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("Thank you for using Hairstory Haircare Assistant! \U0001F4AB")
                return
            conversation_history.append({"role": "user", "content": user_input})
            # Use function calling to extract as much of the profile as possible
            extracted = build_profile_with_function_call(
                [{"role": "system", "content": "You are a warm, friendly haircare assistant. You are building a hair profile for the user."}] + conversation_history
            )
            # On first extraction, set user_profile to the returned dict
            if not user_profile:
                user_profile = {k: v for k, v in extracted.items() if v}
            else:
                for field, _ in profile_fields:
                    value = extracted.get(field, None)
                    if value and not user_profile.get(field):
                        user_profile[field] = value
            # Fallback: try mapping for the last input if still missing
            for field in missing_fields:
                if not user_profile.get(field):
                    mapped = map_user_input_to_field_value(field, user_input)
                    if mapped:
                        user_profile[field] = mapped
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
                # New: Invite user to ask questions about products, update, or quit
                while True:
                    next_action = input("Do you have any questions about these products, or would you like to update your hair profile? (Type your question, 'update', or 'quit'): ").strip().lower()
                    if next_action == "quit":
                        print("Thank you for using Hairstory Haircare Assistant! \U0001F4AB")
                        return
                    elif next_action == "update":
                        print("Which aspect would you like to update?")
                        for idx, (field, prompt) in enumerate(profile_fields, 1):
                            print(f"{idx}. {field.replace('_', ' ').capitalize()} (current: {user_profile[field]})")
                        try:
                            field_idx = int(input("Enter the number of the field to update: ")) - 1
                            if 0 <= field_idx < len(profile_fields):
                                user_profile[profile_fields[field_idx][0]] = None
                                break  # Exit question loop to update profile
                            else:
                                print("Invalid selection. Returning to main menu.")
                        except ValueError:
                            print("Invalid input. Returning to main menu.")
                    else:
                        # Treat as a product-related question
                        # Use the same product context as before
                        products_context = "\n".join([
                            f"{i+1}. {p['name']} - {p['subtitle']} (Type: {p['type']}, URL: {p['url']})" for i, p in enumerate(formatted_products)
                        ])
                        question_prompt = f"The user asked: '{next_action}'. Here are the relevant products you just recommended:\n{products_context}\n\nPlease answer the user's question using only the information above. If the answer is not clear from the product info, say so politely."
                        followup_response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "You are a warm, knowledgeable haircare assistant for Hairstory. Answer user questions about the recommended products using only the provided product information."},
                                {"role": "user", "content": question_prompt}
                            ],
                            max_tokens=300,
                            temperature=0.7
                        )
                        answer = followup_response.choices[0].message.content
                        print("\n💡 Hairstory Assistant:")
                        print(answer)
                        print("\n" + "="*50 + "\n")
            except Exception as e:
                print(f"❌ Sorry, I encountered an error: {str(e)}")
                print("Please try again or rephrase your answer.\n")
                user_profile[profile_fields[0][0]] = None
        else:
            print("Let's continue building your hair profile.")

if __name__ == "__main__":
    chat_with_user() 
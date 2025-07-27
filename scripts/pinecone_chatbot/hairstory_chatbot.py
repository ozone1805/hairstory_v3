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
    ("scalp_condition", "How would you describe your scalp condition? (e.g., dry, oily, normal)"),
    ("length", "How long is your hair? (short, medium, long)")
]

def map_user_input_to_field_value(field, user_input):
    """Map natural language user input to valid field values."""
    text = user_input.strip().lower()
    if field == "hair_type":
        if any(word in text for word in ["straight", "no curl", "no wave", "flat", "sleek", "silky", "smooth", "poker straight"]):
            return "straight"
        if any(word in text for word in ["wavy", "wave", "loose wave", "beachy", "slight wave", "barely wavy", "natural wave"]):
            return "wavy"
        if any(word in text for word in ["curly", "curl", "ringlet", "bouncy", "frizzy", "defined curls", "spiral"]):
            return "curly"
        if any(word in text for word in ["coily", "kinky", "tight curl", "springy", "afro-textured", "slinky-like", "coils"]):
            return "coily"
    elif field == "scalp_condition":
        if any(word in text for word in ["dry", "flaky", "parched", "itchy", "tight feeling", "peeling", "scaly"]):
            return "dry"
        if any(word in text for word in ["oily", "greasy", "need to wash often", "build-up", "shiny", "dirty fast", "heavy roots"]):
            return "oily"
        if any(word in text for word in ["normal", "balanced", "average", "healthy", "fine", "no issues"]):
            return "normal"
    elif field == "length":
        if any(word in text for word in ["short", "pixie", "bob", "ear length", "chin length", "above shoulders"]):
            return "short"
        if any(word in text for word in ["medium", "shoulder", "mid-length", "mid length", "collarbone", "lob", "kind of in between"]):
            return "medium"
        if any(word in text for word in ["long", "waist", "chest", "below shoulder", "past shoulders", "mid-back", "waist length"]):
            return "long"
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

def create_recommendation_prompt(user_input, products, conversation_history=None, user_profile=None):
    """Create a prompt for the OpenAI API with user input, relevant products, and full conversation context."""
    
    products_text = ""
    for i, product in enumerate(products, 1):
        products_text += f"""
{i}. {product['name']}
   - {product['subtitle']}
   - Type: {product['type']}
   - URL: {product['url']}
   - Relevance Score: {product['similarity_score']:.3f}
"""
    
    # Build comprehensive context
    context_parts = []
    
    if user_profile:
        context_parts.append(f"USER'S HAIR PROFILE: {profile_to_string(user_profile)}")
    
    if conversation_history:
        # Include key conversation points for context
        conversation_summary = "CONVERSATION CONTEXT:\n"
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            if msg["role"] == "user":
                conversation_summary += f"- User: {msg['content']}\n"
        context_parts.append(conversation_summary)
    
    context_parts.append(f"USER'S INPUT: {user_input}")
    
    context = "\n\n".join(context_parts)
    
    prompt = f"""You are a warm, understanding haircare assistant for Hairstory. Your goal is to help users find the perfect haircare routine based on their needs.

{context}

RELEVANT HAIRSTORY PRODUCTS (ranked by relevance):
{products_text}

INSTRUCTIONS:
1. Analyze the user's hair type, concerns, and needs from their input and conversation history
2. Consider their complete hair profile when making recommendations
3. Recommend specific products from the list above that would work best for them
4. Explain why these products are a good match for their hair type/concerns
5. Be warm, supportive, and educational
6. Only recommend products from the Hairstory catalog above
7. Include the product URLs when recommending products
8. Reference specific details from the conversation to show you understand their needs
9. If no products seem relevant, ask clarifying questions about their hair type and concerns

Please provide a personalized recommendation:"""

    return prompt

# Add a function to generate the next conversational question using OpenAI

def generate_next_question(profile, conversation_history):
    """Generate the next conversational question with full context including profile and chat history."""
    missing_fields = [field for field, _ in profile_fields if not profile.get(field)]
    if not missing_fields:
        return None
    
    # Build a comprehensive context including the current profile and conversation history
    profile_summary = profile_to_string(profile)
    last_user_message = conversation_history[-1]["content"] if conversation_history else ""
    
    # Create a context-aware prompt that includes the full conversation history
    context_messages = [
        {"role": "system", "content": "You are a warm, friendly haircare assistant building a hair profile. You have access to the user's conversation history and current profile information."},
    ]
    
    # Add conversation history for context
    for msg in conversation_history:
        context_messages.append(msg)
    
    # Add the current profile context
    profile_context = f"Current hair profile information: {profile_summary}"
    if missing_fields:
        profile_context += f"\nStill need to learn about: {', '.join(missing_fields)}"
    
    context_messages.append({
        "role": "user", 
        "content": f"{profile_context}\n\nBased on our conversation so far, please ask a natural, context-aware question to learn about the user's {missing_fields[0].replace('_', ' ')}. Be conversational and reference what they've already told us."
    })
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=context_messages,
        max_tokens=150,
        temperature=0.7
    )
    ai_content = response.choices[0].message.content
    return ai_content.strip() if ai_content else ""

def build_profile_with_function_call(conversation_history, current_profile=None):
    """Use OpenAI function calling to extract as much of the hair profile as possible from the conversation, maintaining existing profile data."""
    if current_profile is None:
        current_profile = {}
    
    # Create a comprehensive context that includes the current profile
    profile_context = ""
    if current_profile:
        profile_context = f"\n\nCurrent profile information: {profile_to_string(current_profile)}"
    
    # Build messages with full context
    messages = [
        {"role": "system", "content": f"You are a warm, friendly haircare assistant building a hair profile. Extract and update the user's hair profile from the conversation, maintaining any existing information.{profile_context}"}
    ]
    
    # Add the full conversation history
    messages.extend(conversation_history)
    
    function_schema = [
        {
            "name": "build_hair_profile",
            "description": "Extract and normalize the user's hair profile from natural language, even if indirect, vague, or poetic. Always return the best matching value for each field, mapping descriptive terms to the closest structured option. If the user has already provided information in earlier messages, retain and merge it. Only update fields that are mentioned or can be inferred from the conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hair_type": {
                        "type": "string",
                        "enum": ["straight", "wavy", "curly", "coily"],
                        "description": "Identify the closest match for the user's hair texture. Map indirect descriptions to these categories. For example:\n- 'flat', 'sleek', 'silky', 'no texture', 'smooth', 'poker straight' → straight\n- 'loose bends', 'beachy', 'slight wave', 'barely wavy', 'natural wave' → wavy\n- 'bouncy', 'frizzy', 'ringlets', 'defined curls', 'spiral' → curly\n- 'tight curls', 'springy', 'kinky', 'afro-textured', 'slinky-like', 'coils' → coily"
                    },
                    "scalp_condition": {
                        "type": "string",
                        "enum": ["dry", "oily", "normal"],
                        "description": "Normalize scalp descriptions to these categories. For example:\n- 'flaky', 'itchy', 'tight feeling', 'peeling', 'scaly' → dry\n- 'greasy', 'build-up', 'shiny', 'dirty fast', 'heavy roots', 'oily' → oily\n- 'balanced', 'healthy', 'fine', 'no issues mentioned', 'normal' → normal"
                    },
                    "length": {
                        "type": "string",
                        "enum": ["short", "medium", "long"],
                        "description": "Map approximate or descriptive lengths to one of these categories:\n- 'pixie', 'ear length', 'chin length', 'above shoulders', 'short' → short\n- 'shoulder length', 'collarbone', 'bob', 'lob', 'kind of in between', 'mid-length' → medium\n- 'past shoulders', 'mid-back', 'waist length', 'long', 'below shoulders' → long"
                    }
                },
                "required": []
            }
        }
    ]
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        functions=function_schema,
        function_call={"name": "build_hair_profile"},
        max_tokens=300,
        temperature=0
    )
    choice = response.choices[0]
    if choice.finish_reason == "function_call":
        args = json.loads(choice.message.function_call.arguments)
        # Merge with existing profile, only updating fields that have values
        updated_profile = current_profile.copy()
        for field, value in args.items():
            if value:  # Only update if we have a value
                updated_profile[field] = value
        return updated_profile
    return current_profile

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
import os
import openai
from pinecone import Pinecone
import json
from typing import Optional, Dict, List
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global debug mode flag
DEBUG_MODE = True

def set_debug_mode(enabled: bool):
    """Set debug mode for logging."""
    global DEBUG_MODE
    DEBUG_MODE = enabled
    if DEBUG_MODE:
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.WARNING)

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

def load_products_data():
    """Load products data from JSON file for catalog summary."""
    try:
        with open('data/all_products.json', 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        if DEBUG_MODE:
            logger.info(f"✅ Loaded {len(products)} products for catalog summary")
        
        return products
    except Exception as e:
        logger.error(f"❌ Error loading products data: {e}")
        return []

def create_product_catalog_summary(products: List[Dict]) -> str:
    """Create a concise summary of all products for system context."""
    summary_parts = []
    
    # Group products by type
    product_types = {}
    for product in products:
        product_type = product.get('type', 'other')
        if product_type not in product_types:
            product_types[product_type] = []
        product_types[product_type].append(product)
    
    # Create summary by type
    for product_type, type_products in product_types.items():
        summary_parts.append(f"\n{product_type.upper()} PRODUCTS:")
        for product in type_products:
            summary_parts.append(f"• {product['name']} - {product['subtitle']}")
            if product.get('benefits'):
                # Take first benefit line
                benefits = product['benefits'].split('\n')[0]
                summary_parts.append(f"  Benefits: {benefits}")
    
    return "\n".join(summary_parts)

def get_embedding(text):
    """Get embedding for text using OpenAI."""
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        if DEBUG_MODE:
            logger.info(f"✅ API RESPONSE - Embeddings: Successfully received embedding (dimensions: {len(response.data[0].embedding)})")
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"❌ Error getting embedding: {e}")
        raise

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
            "details": product.metadata.get("details", ""),
            "benefits": product.metadata.get("benefits", ""),
            "how_to_use": product.metadata.get("how_to_use", ""),
            "ingredients": product.metadata.get("ingredients", ""),
            "set_includes": product.metadata.get("set_includes", ""),
            "similarity_score": product.score
        })
    return formatted_products

# Define profile fields and mapping functions
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
    """Check if user profile is complete."""
    if not profile:
        return False
    return all(profile.get(field) for field, _ in profile_fields)

def profile_to_string(profile):
    """Convert profile to string representation."""
    return ", ".join(f"{field.replace('_', ' ').capitalize()}: {profile.get(field, 'Not provided')}" for field, _ in profile_fields)

def print_profile(profile):
    """Print the current user profile."""
    print("\n📝 Your Hair Profile:")
    for field, _ in profile_fields:
        value = profile.get(field, "Not provided")
        print(f"  {field.replace('_', ' ').capitalize()}: {value}")
    print()

def create_system_instructions(catalog_summary: str) -> str:
    """Create system instructions with product catalog summary."""
    return f"""You are a warm, understanding haircare assistant for Hairstory. Your goal is to help users find the perfect haircare routine based on their needs.

COMPLETE PRODUCT CATALOG SUMMARY:
{catalog_summary}

INSTRUCTIONS:
1. Analyze the user's hair type, concerns, and needs from their input and conversation history
2. Consider their complete hair profile when making recommendations
3. Recommend specific products from the catalog above that would work best for them
4. Explain why these products are a good match for their hair type/concerns
5. Be warm, supportive, and educational
6. Only recommend products from the Hairstory catalog above
7. Include the product URLs when recommending products
8. Reference specific details from the conversation to show you understand their needs
9. If no products seem relevant, ask clarifying questions about their hair type and concerns
10. You can suggest product combinations and routines based on the user's needs
11. Be specific about which products work best for different hair types and concerns

IMPORTANT: Always base your recommendations on the actual product data provided above. Do not make up or reference products that are not in this catalog."""

def create_recommendation_prompt(user_input: str, products: List[Dict], conversation_history: List[Dict] = None, user_profile: Dict = None) -> str:
    """Create a prompt for generating personalized product recommendations."""
    
    # Format the retrieved products with full details
    products_text = ""
    for i, product in enumerate(products, 1):
        products_text += f"""
{i}. {product['name']}
   - Subtitle: {product['subtitle']}
   - Type: {product['type']}
   - URL: {product['url']}
   - Similarity Score: {product['similarity_score']:.3f}"""
        
        if product.get('details'):
            products_text += f"\n   - Details: {product['details']}"
        
        if product.get('benefits'):
            products_text += f"\n   - Benefits: {product['benefits']}"
        
        if product.get('how_to_use'):
            products_text += f"\n   - How to Use: {product['how_to_use']}"
        
        if product.get('set_includes'):
            products_text += f"\n   - Set Includes: {', '.join(product['set_includes']) if isinstance(product['set_includes'], list) else product['set_includes']}"
    
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
    
    return f"""Please provide a personalized recommendation based on the user's needs:

{context}

SEMANTICALLY RELEVANT PRODUCTS (ranked by similarity):
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
10. Make your response feel conversational and natural, not like a product catalog
11. Acknowledge their hair journey and be encouraging about their goals
12. Use their exact words when referencing what they've told you about their hair

Please provide a personalized recommendation that feels like a friendly conversation with a haircare expert:"""

def generate_next_question(profile: Dict, conversation_history: List[Dict]) -> Optional[str]:
    """Generate the next conversational question to complete the user profile."""
    missing_fields = [field for field, _ in profile_fields if not profile.get(field)]
    if not missing_fields:
        return None
    
    # Build context for the question generation
    profile_summary = profile_to_string(profile)
    last_user_message = conversation_history[-1]["content"] if conversation_history else ""
    
    prompt = f"""You are a warm, friendly haircare assistant building a hair profile through natural conversation.

IMPORTANT GUIDELINES:
1. Acknowledge what the user has already shared before asking new questions
2. Ask only ONE question at a time - don't overwhelm them
3. Make questions feel conversational, not like a form
4. Reference their previous answers to show you're listening
5. If they've shared multiple pieces of information, acknowledge them first
6. Be encouraging and supportive about their hair journey
7. Use their exact words when referencing what they've told you

Current Profile: {profile_summary}
Last User Message: {last_user_message}
Missing Fields: {', '.join(missing_fields)}

Based on our conversation so far, please ask a natural, context-aware question to learn about the user's {missing_fields[0].replace('_', ' ')}. First acknowledge what they've already shared, then ask your question in a conversational way.

Question:"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.8
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ Error generating next question: {e}")
        # Fallback to a simple question
        field, question = profile_fields[0]
        return question

def chat_with_user():
    """Main chat function."""
    print("🌟 Welcome to Hairstory Haircare Assistant!")
    print("I'm here to help you find the perfect haircare routine for your unique hair.")
    print("Let's start by getting to know your hair a little better - no pressure, just a friendly chat!")
    print("Type 'quit' to exit at any time.\n")
    
    # Load products data for catalog summary
    products = load_products_data()
    catalog_summary = create_product_catalog_summary(products)
    system_instructions = create_system_instructions(catalog_summary)
    
    # Initialize conversation
    conversation_history = []
    user_profile = {}
    
    # Add system message
    conversation_history.append({
        "role": "system",
        "content": system_instructions
    })
    
    # Add a warm initial message to set the tone
    initial_message = "Hi! I'd love to help you find the perfect haircare products. Tell me a bit about your hair - what's your hair story?"
    print(f"💬 {initial_message}")
    conversation_history.append({"role": "assistant", "content": initial_message})
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\n👋 Thank you for sharing your hair story with me! Have a wonderful day!")
                break
            
            if not user_input:
                continue
            
            # Add user message to history
            conversation_history.append({"role": "user", "content": user_input})
            
            # Update profile if we can extract information
            for field, _ in profile_fields:
                if not user_profile.get(field):
                    value = map_user_input_to_field_value(field, user_input)
                    if value:
                        user_profile[field] = value
                        if DEBUG_MODE:
                            logger.info(f"✅ Updated profile: {field} = {value}")
            
            # Check if profile is complete
            if not is_profile_complete(user_profile):
                next_question = generate_next_question(user_profile, conversation_history)
                if next_question:
                    print(f"\n💬 {next_question}")
                    conversation_history.append({"role": "assistant", "content": next_question})
                    continue
            
            # Query Pinecone for relevant products
            pinecone_results = query_pinecone(user_input, top_k=5)
            relevant_products = format_products_for_prompt(pinecone_results)
            
            if DEBUG_MODE:
                logger.info(f"✅ Retrieved {len(relevant_products)} relevant products from Pinecone")
            
            # Generate recommendation
            recommendation_prompt = create_recommendation_prompt(user_input, relevant_products, conversation_history, user_profile)
            
            # Add the recommendation prompt to conversation
            conversation_history.append({"role": "user", "content": recommendation_prompt})
            
            # Get response from OpenAI
            response = client.chat.completions.create(
                model="gpt-4",
                messages=conversation_history,
                max_tokens=1000,
                temperature=0.7
            )
            
            assistant_response = response.choices[0].message.content.strip()
            
            # Add assistant response to history
            conversation_history.append({"role": "assistant", "content": assistant_response})
            
            # Print response
            print(f"\n💡 {assistant_response}\n")
            
            # Show current profile
            if DEBUG_MODE:
                print_profile(user_profile)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error(f"❌ Error in chat: {e}")
            print(f"\n❌ Sorry, I encountered an error. Please try again.")

if __name__ == "__main__":
    chat_with_user() 
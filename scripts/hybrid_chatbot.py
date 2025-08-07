import os
import json
import logging
import openai
from typing import List, Dict, Optional
from tqdm import tqdm

# Pinecone imports commented out for conversations-only approach
# from pinecone import Pinecone, ServerlessSpec

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")  # Commented out for conversations-only approach
# PINECONE_ENV = os.getenv("PINECONE_ENV")  # Commented out for conversations-only approach

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be set as environment variable.")

# Create OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Pinecone setup commented out for conversations-only approach
# pc = Pinecone(api_key=PINECONE_API_KEY)
# index_name = "hairstory-products"
# index = pc.Index(index_name)

# Debug mode flag
DEBUG_MODE = False

def set_debug_mode(enabled: bool):
    """Set debug mode for detailed logging."""
    global DEBUG_MODE
    DEBUG_MODE = enabled

def load_products_data():
    """Load products data from JSON file."""
    # Try enhanced_products.json first (has image URLs)
    try:
        with open("data/enhanced_products.json", "r") as f:
            products = json.load(f)
        logger.info(f"✅ Loaded {len(products)} products from data/enhanced_products.json")
        return products
    except FileNotFoundError:
        logger.warning("⚠️ enhanced_products.json not found, trying all_products.json")
        try:
            with open("data/all_products.json", "r") as f:
                products = json.load(f)
            logger.info(f"✅ Loaded {len(products)} products from data/all_products.json")
            return products
        except FileNotFoundError:
            logger.error("❌ No product data files found")
            return []

def create_product_catalog_summary(products: List[Dict]) -> str:
    """Create a concise summary of all products for system context."""
    summary_parts = []
    
    # Check if we have enhanced product data
    has_enhanced_data = any('category' in product for product in products)
    
    if has_enhanced_data:
        # Use enhanced data structure
        # Group products by category
        categories = {}
        for product in products:
            category = product.get('category', 'other')
            if category not in categories:
                categories[category] = []
            categories[category].append(product)
        
        # Create summary by category
        for category, category_products in sorted(categories.items()):
            category_name = category.replace('_', ' ').title()
            summary_parts.append(f"\n{category_name.upper()} PRODUCTS:")
            
            for product in category_products:
                summary_parts.append(f"\n• {product['name']}")
                summary_parts.append(f"  Purpose: {product['subtitle']}")
                
                # Add enhanced description if available
                if product.get('enhanced_description'):
                    summary_parts.append(f"  Description: {product['enhanced_description']}")
                
                # Add hair type compatibility
                hair_types = product.get('hair_types', [])
                if hair_types and hair_types != ['all']:
                    summary_parts.append(f"  Best For: {', '.join(hair_types)} hair")
                
                # Add use cases
                use_cases = product.get('use_cases', [])
                if use_cases:
                    summary_parts.append(f"  Use Cases: {', '.join(use_cases)}")
                
                # Add benefits if available
                if product.get('benefits'):
                    benefits = product['benefits'].replace('\n', '; ')
                    summary_parts.append(f"  Key Benefits: {benefits}")
    else:
        # Fall back to original structure
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

# Pinecone functions commented out for conversations-only approach
# def get_embedding(text):
#     """Get embedding for text using OpenAI."""
#     try:
#         response = client.embeddings.create(
#             model="text-embedding-3-small",
#             input=text
#         )
#         if DEBUG_MODE:
#             logger.info(f"✅ API RESPONSE - Embeddings: Successfully received embedding (dimensions: {len(response.data[0].embedding)})")
#         return response.data[0].embedding
#     except Exception as e:
#         logger.error(f"❌ Error getting embedding: {e}")
#         raise

# def query_pinecone(user_input, top_k=5):
#     """Query Pinecone for similar products."""
#     # Get embedding for user input
#     query_embedding = get_embedding(user_input)
#     
#     # Query Pinecone
#     results = index.query(
#         vector=query_embedding,
#         top_k=top_k,
#         include_metadata=True
#     )
#     
#     return results.matches

# def format_products_for_prompt(products):
#     """Format retrieved products for the prompt."""
#     formatted_products = []
#     for product in products:
#         formatted_products.append({
#             "name": product.metadata.get("name", ""),
#             "subtitle": product.metadata.get("subtitle", ""),
#             "url": product.metadata.get("url", ""),
#             "type": product.metadata.get("type", ""),
#             "details": product.metadata.get("details", ""),
#             "benefits": product.metadata.get("benefits", ""),
#             "how_to_use": product.metadata.get("how_to_use", ""),
#             "ingredients": product.metadata.get("ingredients", ""),
#             "set_includes": product.metadata.get("set_includes", ""),
#             "similarity_score": product.score
#         })
#     return formatted_products

# Define profile fields and mapping functions
profile_fields = [
    ("hair_type", "How would you describe your hair type? (e.g., straight, wavy, curly, coily)"),
    ("scalp_condition", "How would you describe your scalp condition? (e.g., dry, oily, normal)"),
    ("length", "How long is your hair? (short, medium, long)")
]

# Enhanced hair profile system with comprehensive questions
HAIR_PROFILE_QUESTIONS = [
    "Describe your hair texture",
    "What's your hair thickness? (fine, medium, thick)",
    "What are your main hair concerns?",
    "How do you typically style your hair?",
    "What's your desired outcome or hair goals?",
    "How do you cleanse your hair?",
    "Do you have any scalp issues?",
    "How often do you wash your hair?",
    "Is your hair color treated?",
    "Is your hair chemically treated?",
    "Do you use extensions?",
    "What's your current hair length?",
    "How would you describe your hair type? (straight, wavy, curly, coily)",
    "What's your scalp condition? (dry, oily, normal, combination)",
    "What products do you currently use?",
    "What's a good hair day like for you?",
    "What's your hair density? (thin, medium, thick)",
    "Do you have any allergies or sensitivities?",
    "What's your lifestyle like? (active, low-maintenance, etc.)",
    "What's your climate/environment like?"
]

def create_conversational_hair_profile_system() -> str:
    """Create a comprehensive system prompt for conversational hair profiling."""
    return """You are a warm, understanding haircare assistant conducting a natural conversation to understand someone's hair and lifestyle.

CONVERSATION GUIDELINES:
- Be genuinely curious and kind - you're having a dialogue, not administering a quiz
- Acknowledge what they share before asking new questions
- Ask follow-up questions based on their responses
- Don't ask too many questions at once - let the conversation flow naturally
- Reference their exact words to show you're listening
- Be encouraging about their hair journey
- Adapt your questions based on what they've already shared

HAIR PROFILE AREAS TO EXPLORE (ask these organically, not all at once):
1. Hair Texture & Type: How would they describe their hair texture and type?
2. Thickness & Density: Fine, medium, or thick hair?
3. Concerns & Goals: What issues do they want to address? What are their hair goals?
4. Styling Habits: How do they typically style their hair?
5. Cleansing Routine: How often do they wash? What's their current routine?
6. Scalp Health: Any scalp issues or concerns?
7. Chemical Treatments: Color, relaxers, perms, etc.
8. Extensions: Do they use or want extensions?
9. Current Products: What are they using now?
10. Lifestyle Factors: Activity level, climate, maintenance preferences
11. Sensitivities: Any allergies or reactions to products?

CONVERSATION FLOW:
- Start with open-ended questions about their hair story
- Ask follow-up questions based on their responses
- If they mention specific concerns, dive deeper into those
- If they share multiple things, acknowledge each before moving on
- Keep the tone warm and supportive
- Don't rush to recommendations until you have a good understanding

Remember: You're building trust and understanding, not just collecting data points."""

def generate_conversational_response(user_input: str, conversation_history: List[Dict], user_profile: Dict = None, assistant_questions: int = 0) -> str:
    """
    Generate a conversational response using the LLM that can either:
    1. Ask follow-up questions to learn more about their hair
    2. Provide recommendations if enough information is gathered
    3. Continue the natural conversation flow
    """
    if user_profile is None:
        user_profile = {}
    
    # Create a summary of what we know so far
    profile_summary = ""
    if user_profile:
        profile_summary = f"\nWhat we know so far: {profile_to_string(user_profile)}"
    
    # Determine if we have enough information for recommendations
    has_sufficient_info = len(conversation_history) >= 3 and any(
        keyword in user_input.lower() for keyword in 
        ['recommend', 'suggest', 'help', 'routine', 'products', 'what should', 'need']
    )
    
    # Create the conversation context
    conversation_context = ""
    if conversation_history:
        # Include last few messages for context
        recent_messages = conversation_history[-4:]  # Last 4 messages
        conversation_context = "\nRecent conversation:\n"
        for msg in recent_messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_context += f"{role}: {msg['content']}\n"
    
    system_prompt = create_conversational_hair_profile_system()
    
    # Check if we're approaching the 10-question limit
    questions_remaining = 10 - assistant_questions
    
    if has_sufficient_info:
        # We have enough info and user is asking for recommendations
        prompt = f"""You are a warm, understanding haircare assistant. The user is asking for product recommendations.

{conversation_context}
{profile_summary}

User's latest message: {user_input}

Based on what they've shared about their hair, provide a warm, conversational response that:
1. Acknowledges their specific hair concerns and goals
2. Suggests 2-3 specific products that would work well for them
3. Explains why these products are a good match
4. Encourages them to ask questions about the products
5. Maintains a supportive, educational tone

Keep your response conversational and encouraging:"""
    else:
        # Continue building the hair profile
        if questions_remaining <= 0:
            # We've asked enough questions, provide a gentle recommendation
            prompt = f"""You are a warm, understanding haircare assistant. We've learned a lot about the user's hair.

{conversation_context}
{profile_summary}

User's latest message: {user_input}

Based on what they've shared, provide a warm response that:
1. Acknowledges what you've learned about their hair
2. Offers to provide some product recommendations
3. Asks if they'd like specific suggestions
4. Maintains the supportive, conversational tone

Keep it natural and encouraging:"""
        else:
            # Ask a follow-up question
            prompt = f"""You are a warm, understanding haircare assistant building a hair profile through natural conversation.

{conversation_context}
{profile_summary}

User's latest message: {user_input}

Questions asked so far: {assistant_questions}/10

Based on what they've shared, ask ONE natural follow-up question to learn more about their hair. The question should:
1. Acknowledge what they've already shared
2. Ask about a different aspect of their hair or routine
3. Feel conversational, not like a form
4. Show you're listening and care about their hair journey

Keep it warm and natural:"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.8
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ Error generating conversational response: {e}")
        return "I'm having trouble processing that right now. Could you tell me more about your hair?"

def extract_hair_profile_from_conversation(conversation_history: List[Dict]) -> Dict:
    """Extract hair profile information from conversation using LLM."""
    if not conversation_history:
        return {}
    
    # Create a summary of the conversation
    conversation_text = ""
    for msg in conversation_history[-10:]:  # Last 10 messages
        role = "User" if msg["role"] == "user" else "Assistant"
        conversation_text += f"{role}: {msg['content']}\n"
    
    prompt = f"""You are a hair profile extraction assistant. Analyze the following conversation and extract key information about the user's hair.

CONVERSATION:
{conversation_text}

Extract the following information in JSON format (only include fields that are clearly mentioned):
{{
    "hair_type": "straight/wavy/curly/coily",
    "hair_texture": "fine/medium/thick",
    "hair_length": "short/medium/long",
    "scalp_condition": "dry/oily/normal/combination",
    "hair_concerns": ["list", "of", "concerns"],
    "hair_goals": ["list", "of", "goals"],
    "styling_preferences": "description",
    "wash_frequency": "how often they wash",
    "current_products": ["list", "of", "current", "products"],
    "chemical_treatments": "color/relaxer/perm/none",
    "lifestyle": "active/low-maintenance/etc",
    "climate": "dry/humid/cold/etc"
}}

Only include fields where the user has clearly provided information. If a field is not mentioned, omit it from the JSON.

JSON:"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.1
        )
        
        # Parse the JSON response
        import re
        json_match = re.search(r'\{.*\}', response.choices[0].message.content, re.DOTALL)
        if json_match:
            extracted_profile = json.loads(json_match.group())
            if DEBUG_MODE:
                logger.info(f"✅ Extracted profile: {extracted_profile}")
            return extracted_profile
        else:
            logger.warning("⚠️ Could not parse JSON from profile extraction")
            return {}
            
    except Exception as e:
        logger.error(f"❌ Error extracting profile: {e}")
        return {}

# Profile mapping function commented out - no longer needed in conversations-only approach
# The LLM's extract_hair_profile_from_conversation function handles this much better
# def map_user_input_to_field_value(field, user_input):
#     """Map user input to structured field values."""
#     user_input_lower = user_input.lower()
#     
#     if field == "hair_type":
#         if any(word in user_input_lower for word in ["straight", "straighten"]):
#             return "straight"
#         elif any(word in user_input_lower for word in ["wavy", "wave"]):
#             return "wavy"
#         elif any(word in user_input_lower for word in ["curly", "curl"]):
#             return "curly"
#         elif any(word in user_input_lower for word in ["coily", "coil", "kinky"]):
#             return "coily"
#     
#     elif field == "scalp_condition":
#         if any(word in user_input_lower for word in ["dry", "flaky", "itchy"]):
#             return "dry"
#         elif any(word in user_input_lower for word in ["oily", "greasy", "slick"]):
#             return "oily"
#         elif any(word in user_input_lower for word in ["normal", "balanced"]):
#             return "normal"
#         elif any(word in user_input_lower for word in ["combination", "mixed"]):
#             return "combination"
#     
#     elif field == "length":
#         if any(word in user_input_lower for word in ["short", "bob", "pixie"]):
#             return "short"
#         elif any(word in user_input_lower for word in ["medium", "shoulder"]):
#             return "medium"
#         elif any(word in user_input_lower for word in ["long", "past shoulder"]):
#             return "long"
#     
#     return None

def is_profile_complete(profile):
    """Check if the hair profile is complete enough for recommendations."""
    required_fields = ["hair_type", "scalp_condition", "length"]
    return all(profile.get(field) for field in required_fields)

def profile_to_string(profile):
    """Convert profile to readable string."""
    if not profile:
        return "No profile information available"
    
    parts = []
    for field, value in profile.items():
        if value:
            field_name = field.replace('_', ' ').title()
            if isinstance(value, list):
                parts.append(f"{field_name}: {', '.join(value)}")
            else:
                parts.append(f"{field_name}: {value}")
    
    return "; ".join(parts)

def print_profile(profile):
    """Print profile in a readable format."""
    print("\nHAIR PROFILE:")
    for field, value in profile.items():
        if value:
            print(f"  {field.replace('_', ' ').capitalize()}: {value}")
    print()

def create_system_instructions(catalog_summary: str) -> str:
    """Create system instructions with product catalog summary."""
    return f"""You are a warm, understanding haircare assistant for Hairstory. Your goal is to help users find the perfect haircare routine based on their needs.

COMPLETE PRODUCT CATALOG SUMMARY:
{catalog_summary}

RECOMMENDATION GUIDELINES:
1. **ALWAYS START WITH NEW WASH**: New Wash is the foundation of every haircare routine
   - **MANDATORY**: Every recommendation should include an appropriate New Wash variant
   - Fine/Oily Hair: New Wash Deep Clean (removes excess oil and buildup)
   - Dry/Thick Hair: New Wash Rich (provides extra moisture and nourishment)
   - Curly/Coily Hair: New Wash Original or New Wash Rich (gentle cleansing that preserves natural oils)
   - Damaged Hair: New Wash Original with Bond Boost (gentle cleansing + repair)
   - All Hair Types: New Wash Original (universal gentle cleanser)

2. **Hair Type Matching**: After New Wash, add complementary products
   - Fine/Oily: Powder, Root Lift (for volume and oil control)
   - Dry/Thick: Hair Balm, Oil (for moisture and definition)
   - Curly/Coily: Hair Balm, Oil, Undressed (for definition and frizz control)
   - Damaged: Bond Serum (for repair and strengthening)
   - All Hair Types: Primer (for heat protection and styling prep)

3. **Product Categories**: Understand the complete routine structure
   - **Foundation**: New Wash (always required)
   - Pre-Cleansing: Pre-Wash for buildup removal (before New Wash)
   - Pre-Styling: Primer for heat protection (after New Wash)
   - Styling: Products for texture, volume, definition (after New Wash)
   - Damage Repair: Bond products for damaged hair (mixed with New Wash)
   - Color Maintenance: Color Boost products for color-treated hair (after New Wash)
   - Accessories: Tools for application and convenience

3. **Use Case Understanding**: Match products to specific needs
   - Volume: Root Lift, Powder
   - Moisture: Hair Balm, Oil, New Wash Rich
   - Damage Repair: Bond Boost + Bond Serum
   - Texture: Undressed, Wax
   - Color Maintenance: Purple/Blue/Red Color Boost
   - Travel: Travel Bottle
   - Refills: Cost-effective options for regular users
   - Trial Kits: Risk-free testing for new users
   - Bundles: Complete routines for specific needs
   - Premium: Maximum benefits for comprehensive care

4. **Bundle Recommendations**: Know when to suggest complete routines
   - Starter Bundles: For new users or complete routine seekers
   - Damage Repair Bundles: For damaged hair needing comprehensive repair
   - Styling Bundles: For texture and definition routines
   - Clarifying Bundles: For buildup removal and hair reset
   - Premium Bundles: For comprehensive care and maximum benefits

5. **Product Relationships**: Understand which products work together
   - Bond Boost must be mixed with New Wash
   - Primer works before any heat styling
   - Color Boost products maintain specific hair colors
   - Refills are cost-effective alternatives to full products
   - Trial Kits are perfect for new users who want to test before committing
   - Bundles save money compared to buying products individually

INSTRUCTIONS:
1. **MANDATORY**: ALWAYS start recommendations with an appropriate New Wash variant - this is the foundation of every haircare routine
2. Analyze the user's hair type, concerns, and needs from their input and conversation history
3. Consider their complete hair profile when making recommendations
4. Recommend New Wash first, then add 2-3 complementary products that work well with New Wash
5. Explain why New Wash is essential and why these products work together as a complete routine
6. Be warm, supportive, and educational
7. Only recommend products from the Hairstory catalog above
8. Include the product URLs when recommending products
9. Reference specific details from the conversation to show you understand their needs
10. If no products seem relevant, ask clarifying questions about their hair type and concerns
11. You can suggest product combinations and routines based on the user's needs
12. Be specific about which products work best for different hair types and concerns
13. Always explain how New Wash works as the foundation and how other products complement it

IMPORTANT: Always base your recommendations on the actual product data provided above. Do not make up or reference products that are not in this catalog."""

# Pinecone recommendation prompt function commented out for conversations-only approach
# def create_recommendation_prompt(user_input: str, products: List[Dict], conversation_history: List[Dict] = None, user_profile: Dict = None) -> str:
#     """Create a prompt for generating personalized product recommendations."""
#     
#     # Format the retrieved products with full details
#     products_text = ""
#     for i, product in enumerate(products, 1):
#         products_text += f"""
# {i}. {product['name']}
#    - Subtitle: {product['subtitle']}
#    - Type: {product['type']}
#    - URL: {product['url']}
#    - Similarity Score: {product['similarity_score']:.3f}"""
#         
#         if product.get('details'):
#             products_text += f"\n   - Details: {product['details']}"
#         
#         if product.get('benefits'):
#             products_text += f"\n   - Benefits: {product['benefits']}"
#         
#         if product.get('how_to_use'):
#             products_text += f"\n   - How to Use: {product['how_to_use']}"
#         
#         if product.get('set_includes'):
#             products_text += f"\n   - Set Includes: {', '.join(product['set_includes']) if isinstance(product['set_includes'], list) else product['set_includes']}"
#     
#     # Build comprehensive context
#     context_parts = []
#     
#     if user_profile:
#         context_parts.append(f"USER'S HAIR PROFILE: {profile_to_string(user_profile)}")
#     
#     if conversation_history:
#         # Include key conversation points for context
#         conversation_summary = "CONVERSATION CONTEXT:\n"
#         for msg in conversation_history[-5:]:  # Last 5 messages for context
#             if msg["role"] == "user":
#                 conversation_summary += f"- User: {msg['content']}\n"
#         context_parts.append(conversation_summary)
#     
#     context_parts.append(f"USER'S INPUT: {user_input}")
#     
#     context = "\n\n".join(context_parts)
#     
#     return f"""Please provide a personalized recommendation based on the user's needs:
# 
# {context}
# 
# SEMANTICALLY RELEVANT PRODUCTS (ranked by similarity):
# {products_text}
# 
# INSTRUCTIONS:
# 1. Analyze the user's hair type, concerns, and needs from their input and conversation history
# 2. Consider their complete hair profile when making recommendations
# 3. Recommend specific products from the list above that would work best for them
# 4. Explain why these products are a good match for their hair type/concerns
# 5. Be warm, supportive, and educational
# 6. Only recommend products from the Hairstory catalog above
# 7. Include the product URLs when recommending products
# 8. Reference specific details from the conversation to show you understand their needs
# 9. If no products seem relevant, ask clarifying questions about their hair type and concerns
# 10. Make your response feel conversational and natural, not like a product catalog
# 11. Acknowledge their hair journey and be encouraging about their goals
# 12. Use their exact words when referencing what they've told you about their hair
# 
# Please provide a personalized recommendation that feels like a friendly conversation with a haircare expert:"""

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
            model="gpt-4o-mini",
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
    """Main chat function using conversational hair profiling."""
    print("💬 Welcome to the Hairstory Haircare Assistant!")
    print("I'm here to help you find the perfect haircare routine. Let's start by learning about your hair.")
    print("(Type 'quit' to exit)\n")
    
    conversation_history = []
    user_profile = {}
    
    # Start with an initial question
    initial_message = "Tell me about your hair! What's your hair story?"
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
            
            # Extract hair profile information from the conversation
            extracted_profile = extract_hair_profile_from_conversation(conversation_history)
            if extracted_profile:
                user_profile.update(extracted_profile)
                if DEBUG_MODE:
                    logger.info(f"✅ Updated profile from conversation: {extracted_profile}")
            
            # Generate conversational response
            response = generate_conversational_response(user_input, conversation_history, user_profile)
            print(f"\n💬 {response}")
            conversation_history.append({"role": "assistant", "content": response})
            
            # CONVERSATIONS-ONLY APPROACH: No Pinecone query
            # pinecone_results = query_pinecone(user_input, top_k=5)  # Commented out
            # relevant_products = format_products_for_prompt(pinecone_results)  # Commented out
            
            if DEBUG_MODE:
                logger.info(f"✅ Using conversations-only approach for recommendations")
            
            # Generate recommendation using conversations-only approach
            # recommendation_prompt = create_recommendation_prompt(user_input, relevant_products, conversation_history, user_profile)  # Commented out
            
            # Add the recommendation prompt to conversation
            # conversation_history.append({"role": "user", "content": recommendation_prompt})  # Commented out
            
            # Get response from OpenAI
            # response = client.chat.completions.create(  # Commented out
            #     model="gpt-4o-mini",  # Commented out
            #     messages=[  # Commented out
            #         {"role": "system", "content": system_instructions},  # Commented out
            #         {"role": "user", "content": recommendation_prompt}  # Commented out
            #     ],  # Commented out
            #     max_tokens=800,  # Commented out
            #     temperature=0.7  # Commented out
            # )  # Commented out
            
            # recommendation = response.choices[0].message.content  # Commented out
            # print(f"\n💡 RECOMMENDATION: {recommendation}")  # Commented out
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Have a wonderful day!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Let's continue our conversation. Tell me more about your hair!")

if __name__ == "__main__":
    chat_with_user() 
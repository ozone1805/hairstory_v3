from flask import Flask, request, jsonify, Response
import os
import logging
import json
import re
from scripts.hybrid_chatbot import (
    load_products_data,
    create_product_catalog_summary,
    # query_pinecone,  # Commented out for conversations-only approach
    # format_products_for_prompt,  # Commented out for conversations-only approach
    create_system_instructions,
    # create_recommendation_prompt,  # Commented out - replaced with create_conversations_only_prompt
    profile_to_string,
    is_profile_complete,
    profile_fields,
    generate_next_question,
    # map_user_input_to_field_value,  # Commented out - no longer needed in conversations-only approach
    generate_conversational_response,
    extract_hair_profile_from_conversation,
    client,
    set_debug_mode
)
import re
from typing import List, Dict

# Debug mode configuration
DEBUG_MODE = False  # Set to False to disable detailed API logging

# Set debug mode in the chatbot module
set_debug_mode(DEBUG_MODE)

# Set up logging based on debug mode
if DEBUG_MODE:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load products data and create catalog summary once at startup
try:
    products = load_products_data()
    catalog_summary = create_product_catalog_summary(products)
    system_instructions = create_system_instructions(catalog_summary)
    logger.info(f"✅ Loaded {len(products)} products and created catalog summary")
except Exception as e:
    logger.error(f"❌ Error loading products data: {e}")
    products = []
    catalog_summary = "Error loading product catalog"
    system_instructions = "You are a haircare assistant. Please inform the user that there was an error loading the product catalog."

def extract_product_images(text: str, products: List[Dict]) -> List[Dict]:
    """Extract product names from text and return their image URLs."""
    product_images = []
    text_lower = text.lower()
    
    # Create a mapping of product names to their images
    product_name_to_image = {}
    for product in products:
        # Store both full name and common variations
        product_name = product['name'].lower()
        product_name_to_image[product_name] = {
            'name': product['name'],
            'img_url': product.get('img_url', ''),
            'url': product.get('url', '')
        }
        
        # Also store common variations (e.g., "New Wash Original" -> "new wash")
        if 'new wash' in product_name:
            product_name_to_image['new wash'] = product_name_to_image[product_name]
        if 'pre-wash' in product_name or 'pre wash' in product_name:
            product_name_to_image['pre wash'] = product_name_to_image[product_name]
        if 'hair balm' in product_name:
            product_name_to_image['hair balm'] = product_name_to_image[product_name]
        if 'bond boost' in product_name:
            product_name_to_image['bond boost'] = product_name_to_image[product_name]
        if 'bond serum' in product_name:
            product_name_to_image['bond serum'] = product_name_to_image[product_name]
    
    # Extract product names from text (case insensitive)
    found_products = set()  # To avoid duplicates
    for product_name, product_info in product_name_to_image.items():
        if product_name in text_lower and product_info['name'] not in found_products:
            product_images.append(product_info)
            found_products.add(product_info['name'])
    
    return product_images



@app.route("/")
def home():
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hairstory Haircare Assistant (Conversations-Only)</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f7f7f7; margin: 0; padding: 0; }
            .container { max-width: 500px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 24px; }
            h2 { text-align: center; color: #333; }
            .subtitle { text-align: center; color: #666; font-size: 14px; margin-bottom: 20px; }
            #chat { height: 350px; overflow-y: auto; border: 1px solid #eee; border-radius: 6px; padding: 12px; background: #fafafa; margin-bottom: 16px; }
            .msg { margin: 8px 0; line-height: 1.5; }
            .user { color: #1a73e8; }
            .bot { color: #388e3c; }
            .msg h3 { margin: 8px 0 4px 0; color: #333; font-size: 16px; }
            .msg h4 { margin: 6px 0 3px 0; color: #333; font-size: 14px; }
            .msg ul { margin: 4px 0; padding-left: 20px; }
            .msg li { margin: 2px 0; }
            .msg strong { font-weight: bold; }
            .msg em { font-style: italic; }
            .msg a { color: #1a73e8; text-decoration: underline; }
            .msg a:hover { color: #0d47a1; text-decoration: none; }
            .typing-indicator .dots { display: inline-block; min-width: 20px; }
            .product-images { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
            .product-image-container { text-align: center; }
            .product-image { width: 80px; height: 80px; object-fit: cover; border-radius: 8px; cursor: pointer; border: 2px solid #e0e0e0; transition: border-color 0.2s; }
            .product-image:hover { border-color: #1a73e8; }
            .product-name { font-size: 11px; color: #666; margin-top: 4px; max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            #input-area { display: flex; }
            #user-input { flex: 1; padding: 8px; border-radius: 4px; border: 1px solid #ccc; }
            #send-btn { padding: 8px 16px; border: none; background: #1a73e8; color: #fff; border-radius: 4px; margin-left: 8px; cursor: pointer; }
            #send-btn:disabled { background: #aaa; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Hairstory Haircare Assistant</h2>
            <div class="subtitle">Powered by Conversations API: Fast & Knowledgeable</div>
            <div id="chat"></div>
            <form id="input-area" autocomplete="off">
                <input id="user-input" autocomplete="off" placeholder="Type your message..." required />
                <button id="send-btn" type="submit">Send</button>
            </form>
        </div>
        <script src="/static/chatbot.js"></script>
    </body>
    </html>
    '''
    return Response(html, mimetype='text/html')

@app.route("/static/chatbot.js")
def serve_chatbot_js():
    with open('scripts/JavaScript/chatbot.js', 'r') as f:
        return Response(f.read(), mimetype='application/javascript')

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    conversation_history = data.get("conversation_history", [])
    user_profile = data.get("user_profile", {})

    if DEBUG_MODE:
        logger.info(f"🔄 CHAT REQUEST: Received chat request with {len(conversation_history)} messages in history")
        # Log the last few messages to debug duplication
        if conversation_history:
            logger.info(f"📝 Last 3 messages:")
            for i, msg in enumerate(conversation_history[-3:]):
                logger.info(f"  {i+1}. {msg['role']}: {msg['content'][:50]}...")

    # Extract hair profile information from the conversation using LLM
    if conversation_history:
        extracted_profile = extract_hair_profile_from_conversation(conversation_history)
        if extracted_profile:
            user_profile.update(extracted_profile)
            if DEBUG_MODE:
                logger.info(f"✅ Updated profile from conversation: {extracted_profile}")

    # Count assistant questions (messages from assistant that end with ?)
    assistant_questions = 0
    for msg in conversation_history:
        if msg["role"] == "assistant" and msg["content"].strip().endswith("?"):
            assistant_questions += 1

    # Check if user is asking for recommendations
    last_user_message = conversation_history[-1]["content"] if conversation_history else ""
    is_asking_for_recommendations = any(
        keyword in last_user_message.lower() for keyword in 
        ['recommend', 'suggest', 'help', 'routine', 'products', 'what should', 'need', 'give me']
    )

    # Force recommendations if we've asked 10+ questions or user is explicitly asking
    should_give_recommendations = (
        is_asking_for_recommendations or 
        assistant_questions >= 10 or 
        len(conversation_history) >= 20  # Fallback: force after 20 total messages
    )

    if should_give_recommendations:
        # Give recommendations using conversations-only approach
        profile_text = profile_to_string(user_profile) if user_profile else "Based on our conversation"
        
        # CONVERSATIONS-ONLY APPROACH: No Pinecone query
        # pinecone_results = query_pinecone(profile_text, top_k=5)  # Commented out
        # relevant_products = format_products_for_prompt(pinecone_results)  # Commented out
        
        if DEBUG_MODE:
            logger.info(f"🤖 CONVERSATIONS-ONLY: Using full catalog knowledge for recommendations")
            logger.info(f"📊 Question count: {assistant_questions} assistant questions, {len(conversation_history)} total messages")
        
        # Create recommendation prompt with conversations-only context
        recommendation_prompt = create_conversations_only_prompt(
            profile_text, 
            conversation_history=conversation_history,
            user_profile=user_profile
        )
        
        if DEBUG_MODE:
            logger.info(f"🤖 API CALL - Chat Completions: Generating conversations-only recommendation")
            logger.info(f"📝 Context: Profile: {profile_text}, Catalog Summary: {len(catalog_summary)} chars")
        
        # Call OpenAI with conversations-only approach (system instructions only)
        openai_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": recommendation_prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        recommendation = openai_response.choices[0].message.content
        if DEBUG_MODE:
            logger.info(f"✅ API RESPONSE - Chat Completions: Generated conversations-only recommendation (length: {len(recommendation)} chars)")
        
        # Extract product images from the recommendation
        product_images = extract_product_images(recommendation, products)
        
        response = {
            "profile": user_profile,
            "recommendation": recommendation,
            "product_images": product_images
        }
        return jsonify(response)
    else:
        # Continue the conversational flow
        conversational_response = generate_conversational_response(last_user_message, conversation_history, user_profile, assistant_questions)
        response = {
            "profile": user_profile,
            "message": conversational_response
        }
        return jsonify(response)

def create_conversations_only_prompt(profile_text: str, conversation_history: List[Dict] = None, user_profile: Dict = None) -> str:
    """Create a prompt for conversations-only recommendations using full catalog knowledge."""
    
    # Build comprehensive context
    context_parts = []
    
    if user_profile:
        context_parts.append(f"USER'S HAIR PROFILE: {profile_text}")
    
    if conversation_history:
        # Include key conversation points for context
        conversation_summary = "CONVERSATION CONTEXT:\n"
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            if msg["role"] == "user":
                conversation_summary += f"- User: {msg['content']}\n"
        context_parts.append(conversation_summary)
    
    context = "\n\n".join(context_parts)
    
    return f"""Please provide a personalized recommendation based on the user's needs using your complete product knowledge:

{context}

INSTRUCTIONS:
1. Analyze the user's hair type, concerns, and needs from their input and conversation history
2. Consider their complete hair profile when making recommendations
3. Recommend specific products from the Hairstory catalog that would work best for them
4. Explain why these products are a good match for their hair type/concerns
5. Be warm, supportive, and educational
6. Include product URLs when recommending products
7. Reference specific details from the conversation to show you understand their needs
8. Make your response feel conversational and natural, not like a product catalog
9. Acknowledge their hair journey and be encouraging about their goals
10. Use their exact words when referencing what they've told you about their hair
11. You can suggest product combinations and routines based on the user's needs

Please provide a personalized recommendation that feels like a friendly conversation with a haircare expert:"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))) 
from flask import Flask, request, jsonify, Response
import os
import logging
import json
from scripts.hybrid_chatbot import (
    load_products_data,
    create_product_catalog_summary,
    query_pinecone,
    format_products_for_prompt,
    create_system_instructions,
    create_recommendation_prompt,
    profile_to_string,
    is_profile_complete,
    profile_fields,
    generate_next_question,
    map_user_input_to_field_value,
    generate_conversational_response,
    extract_hair_profile_from_conversation,
    client,
    set_debug_mode
)

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

@app.route("/")
def home():
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hairstory Haircare Assistant (Hybrid)</title>
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
            #input-area { display: flex; }
            #user-input { flex: 1; padding: 8px; border-radius: 4px; border: 1px solid #ccc; }
            #send-btn { padding: 8px 16px; border: none; background: #1a73e8; color: #fff; border-radius: 4px; margin-left: 8px; cursor: pointer; }
            #send-btn:disabled { background: #aaa; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Hairstory Haircare Assistant</h2>
            <div class="subtitle">Powered by Hybrid AI: Semantic Search + Product Knowledge</div>
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
        # Give recommendations - either user asked or we've asked enough questions
        profile_text = profile_to_string(user_profile) if user_profile else "Based on our conversation"
        
        # Query Pinecone for semantically relevant products
        pinecone_results = query_pinecone(profile_text, top_k=5)
        relevant_products = format_products_for_prompt(pinecone_results)
        
        if DEBUG_MODE:
            logger.info(f"🔍 PINECONE QUERY: Retrieved {len(relevant_products)} relevant products")
            logger.info(f"📊 Question count: {assistant_questions} assistant questions, {len(conversation_history)} total messages")
            for i, product in enumerate(relevant_products, 1):
                logger.info(f"   {i}. {product['name']} (Score: {product['similarity_score']:.3f})")
        
        # Create recommendation prompt with hybrid context
        recommendation_prompt = create_recommendation_prompt(
            profile_text, 
            relevant_products, 
            conversation_history=conversation_history,
            user_profile=user_profile
        )
        
        if DEBUG_MODE:
            logger.info(f"🤖 API CALL - Chat Completions: Generating hybrid recommendation")
            logger.info(f"📝 Hybrid Context: Profile: {profile_text}, Products: {len(relevant_products)} items, Catalog Summary: {len(catalog_summary)} chars")
        
        # Call OpenAI with hybrid approach (system instructions + semantic results)
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
            logger.info(f"✅ API RESPONSE - Chat Completions: Generated hybrid recommendation (length: {len(recommendation)} chars)")
        
        response = {
            "profile": user_profile,
            "products": relevant_products,
            "recommendation": recommendation
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))) 
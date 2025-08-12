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
DEBUG_MODE = True  # Set to True to enable detailed API logging

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
    
    if DEBUG_MODE:
        logger.info(f"🔍 Extracting products from text of length: {len(text)}")
        logger.info(f"🔍 Total products loaded: {len(products)}")
        # Check if Undressed is in the products list
        undressed_products = [p for p in products if 'undressed' in p['name'].lower()]
        if undressed_products:
            logger.info(f"🔍 Found Undressed products: {[p['name'] for p in undressed_products]}")
        else:
            logger.warning("⚠️ No Undressed products found in database!")
    
    # Create a mapping of product names to their images
    product_name_to_image = {}
    for product in products:
        # Store both full name and common variations
        product_name = product['name'].lower()
        product_info = {
            'name': product['name'],
            'img_url': product.get('img_url', ''),
            'url': product.get('url', '')
        }
        product_name_to_image[product_name] = product_info
        
        # Debug: Check if Undressed is being loaded
        if 'undressed' in product_name:
            if DEBUG_MODE:
                logger.info(f"🔍 Found Undressed in products: {product['name']}")
        
        # Store specific product variations with proper object copying
        # Only create variations for exact matches to avoid conflicts
        if product_name == 'pre-wash':
            product_name_to_image['pre wash'] = product_info.copy()
        elif product_name == 'hair balm':
            product_name_to_image['hair balm'] = product_info.copy()
        elif product_name == 'bond boost':
            product_name_to_image['bond boost'] = product_info.copy()
        elif product_name == 'bond boost for new wash':
            product_name_to_image['bond boost'] = product_info.copy()
        elif product_name == 'bond serum':
            product_name_to_image['bond serum'] = product_info.copy()
        elif product_name == 'undressed':
            product_name_to_image['undressed'] = product_info.copy()
    
    # Extract product names from text (case insensitive)
    found_products = set()  # To avoid duplicates
    
    # Look for products that are explicitly mentioned as recommendations
    # Check for patterns like "I recommend", "I suggest", "adding", etc.
    recommendation_patterns = [
        'i recommend', 'i suggest', 'adding', 'also suggest', 'also recommend',
        'suggest adding', 'recommend adding', 'try', 'use', 'start with'
    ]
    
    # First, try to find products mentioned in recommendation context
    for product_name, product_info in product_name_to_image.items():
        if product_info['name'] not in found_products:
            # Check if product is mentioned near recommendation keywords
            for pattern in recommendation_patterns:
                if pattern in text_lower and product_name in text_lower:
                    # Find the position of the pattern and product
                    pattern_pos = text_lower.find(pattern)
                    product_pos = text_lower.find(product_name)
                    
                    # If they're within 200 characters of each other, it's likely a recommendation
                    if abs(pattern_pos - product_pos) < 200:
                        if DEBUG_MODE:
                            logger.info(f"🔍 Found recommendation: '{product_info['name']}' near pattern '{pattern}' (distance: {abs(pattern_pos - product_pos)})")
                        product_images.append(product_info)
                        found_products.add(product_info['name'])
                        break
    
    # If no recommendations found, fall back to exact matches
    if not product_images:
        for product_name, product_info in product_name_to_image.items():
            if product_name in text_lower and product_info['name'] not in found_products:
                product_images.append(product_info)
                found_products.add(product_info['name'])
    
    # Final comprehensive check: Look for any product name mentioned anywhere in the text
    # This catches products mentioned in different contexts, but be more selective
    for product_name, product_info in product_name_to_image.items():
        if product_info['name'] not in found_products:
            # Check if the product name appears anywhere in the text (case insensitive)
            # But only if it's not in the reviews section (which might mention alternatives)
            if product_info['name'].lower() in text.lower():
                # Skip if this appears to be in a reviews section or alternative mention
                text_lower = text.lower()
                product_lower = product_info['name'].lower()
                
                # Check if this is likely a recommendation vs just a mention
                is_recommendation = False
                for pattern in recommendation_patterns:
                    if pattern in text_lower:
                        pattern_pos = text_lower.find(pattern)
                        product_pos = text_lower.find(product_lower)
                        if abs(pattern_pos - product_pos) < 300:  # Within 300 chars
                            is_recommendation = True
                            break
                
                if is_recommendation:
                    if DEBUG_MODE:
                        logger.info(f"🔍 Found comprehensive match: '{product_info['name']}'")
                    product_images.append(product_info)
                    found_products.add(product_info['name'])
    
    # Ultra comprehensive check: Look for product name variations and partial matches
    # This handles cases where product names might be mentioned in different forms
    # But be more precise to avoid conflicts between similar products
    product_variations = {
        'new wash original': ['new wash original'],  # Be specific, don't match generic "new wash"
        'new wash rich': ['new wash rich'],  # Be specific, don't match generic "new wash"
        'hair balm': ['hair balm', 'balm'],
        'undressed': ['undressed'],
        'oil': ['oil'],
        'primer': ['primer'],
        'bond boost': ['bond boost'],  # Don't match "bond boost for new wash" with "bond boost"
        'bond boost for new wash': ['bond boost for new wash'],
        'bond serum': ['bond serum'],
        'pre-wash': ['pre-wash', 'pre wash'],
        'red color boost': ['red color boost'],
        'purple color boost': ['purple color boost'],
        'blue color boost': ['blue color boost'],
        'powder': ['powder'],
        'root lift': ['root lift'],
        'wax': ['wax']
    }
    
    for product_name, product_info in product_name_to_image.items():
        if product_info['name'] not in found_products:
            # Check for variations of this product name
            product_lower = product_name.lower()
            if product_lower in product_variations:
                for variation in product_variations[product_lower]:
                    if variation in text.lower():
                        if DEBUG_MODE:
                            logger.info(f"🔍 Found variation match: '{product_info['name']}' via '{variation}'")
                        product_images.append(product_info)
                        found_products.add(product_info['name'])
                        break
    
    # Final fallback: Direct text search for any product name
    # This catches any product mentioned in the text that wasn't found by other methods
    for product_name, product_info in product_name_to_image.items():
        if product_info['name'] not in found_products:
            # Check if the exact product name appears in the text
            if product_info['name'].lower() in text.lower():
                if DEBUG_MODE:
                    logger.info(f"🔍 Found direct match: '{product_info['name']}'")
                product_images.append(product_info)
                found_products.add(product_info['name'])
    
    # Limit results to only the most relevant products (max 4) and ensure they match recommendations
    # Sort by relevance: exact matches first, then partial matches
    final_products = []
    seen_names = set()
    
    # First, prioritize products that are explicitly mentioned in the recommendation text
    # Use exact matching to avoid substitutions
    for product in product_images:
        if product['name'] not in seen_names:
            # Check if the exact product name appears in the text
            product_name_lower = product['name'].lower()
            text_lower = text.lower()
            
            # Look for exact product name match, but only in the main recommendation section
            # Skip products that only appear in reviews or alternative mentions
            if product_name_lower in text_lower:
                # Check if this product is mentioned in the main recommendation section
                # (before any "What customers are saying" section)
                main_section = text_lower
                if "what customers are saying" in text_lower:
                    main_section = text_lower.split("what customers are saying")[0]
                
                if product_name_lower in main_section:
                    final_products.append(product)
                    seen_names.add(product['name'])
                    if DEBUG_MODE:
                        logger.info(f"🔍 Added to final products: '{product['name']}' (main section match)")
                else:
                    if DEBUG_MODE:
                        logger.info(f"🔍 Skipped '{product['name']}' (only in reviews/alternatives)")
    
    # Only add fallback products if we have very few products (less than 2)
    # This prevents adding products that weren't explicitly recommended
    if len(final_products) < 2:
        for product in product_images:
            if product['name'] not in seen_names and len(final_products) < 4:
                final_products.append(product)
                seen_names.add(product['name'])
                if DEBUG_MODE:
                    logger.info(f"🔍 Added to final products: '{product['name']}' (fallback)")
    
    if DEBUG_MODE:
        logger.info(f"🔍 Final products selected: {[p['name'] for p in final_products]}")
    
    return final_products



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
        
        if DEBUG_MODE:
            logger.info(f"🔍 Extracted products: {[p.get('name') for p in product_images]}")
            logger.info(f"🔍 Recommendation text length: {len(recommendation)}")
            # Log the first 500 characters to see what we're working with
            logger.info(f"🔍 Recommendation preview: {recommendation[:500]}...")

        # Fetch positive, relevant review snippets for the recommended products
        try:
            product_titles = [p.get('name') for p in product_images if p.get('name')]
            if DEBUG_MODE:
                logger.info(f"🔍 Looking for reviews for: {product_titles}")
            reviews_by_product = fetch_positive_reviews_for_products(product_titles, user_profile, top_k_per_product=2)
            if DEBUG_MODE:
                logger.info(f"🔍 Found reviews for: {list(reviews_by_product.keys())}")
        except Exception as e:
            if DEBUG_MODE:
                logger.warning(f"⚠️ Skipping reviews fetch due to error: {e}")
            reviews_by_product = {}

        # Append a short customer reviews section if available
        if reviews_by_product:
            reviews_section_parts = ["\n\nWhat customers are saying:"]
            for title, reviews in reviews_by_product.items():
                reviews_section_parts.append(f"\n- **{title}**:")
                for r in reviews:
                    snippet = r.get('review_content', '').strip().replace('\n', ' ')
                    if not snippet:
                        continue
                    # Keep snippets short
                    if len(snippet) > 220:
                        snippet = snippet[:217].rstrip() + '...'
                    reviews_section_parts.append(f"  - \"{snippet}\"")
            recommendation += "\n" + "\n".join(reviews_section_parts)
        
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

def fetch_positive_reviews_for_products(product_titles: List[str], user_profile: Dict = None, top_k_per_product: int = 2) -> Dict[str, List[Dict]]:
    """Fetch positive reviews for specific products from Pinecone reviews index."""
    try:
        from pinecone import Pinecone
        from dotenv import load_dotenv
        load_dotenv()
        
        # Initialize Pinecone
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index("hairstory-reviews")
        
        reviews_by_product = {}
        
        for product_title in product_titles:
            if not product_title:
                continue
                
            # Create a query that matches the product title
            query_text = f"Product: {product_title}"
            
            # Query Pinecone for reviews of this product
            results = index.query(
                vector=client.embeddings.create(
                    model="text-embedding-3-small", 
                    input=query_text
                ).data[0].embedding,
                top_k=top_k_per_product * 5,  # Get more to filter for positive ones
                include_metadata=True
            )
            
            # Filter for positive reviews (score >= 4) and format
            positive_reviews = []
            for match in results.matches:
                metadata = match.metadata
                review_score = metadata.get('review_score', 0)
                review_product_title = metadata.get('product_title', '').lower()
                
                # Check if this review is for the correct product
                # Use more precise matching to avoid partial matches
                product_words = product_title.lower().split()
                # Clean up review product title (remove punctuation, etc.)
                review_words = review_product_title.lower().replace('.', '').replace(',', '').split()
                
                # Check if all words in the product title are in the review product title
                # This prevents "New Wash Original" from matching "New Wash Dispenser with Pump"
                matches = all(word in review_words for word in product_words)
                
                if (review_score >= 4 and  # Only positive reviews
                    matches):  # Product title matches precisely
                    positive_reviews.append({
                        'review_content': metadata.get('review_content', ''),
                        'review_score': review_score,
                        'hair_type': metadata.get('hair_type', ''),
                        'hair_concerns': metadata.get('hair_concerns', '')
                    })
                    
                    if len(positive_reviews) >= top_k_per_product:
                        break
            
            if positive_reviews:
                reviews_by_product[product_title] = positive_reviews
        
        return reviews_by_product
        
    except Exception as e:
        if DEBUG_MODE:
            logger.error(f"Error fetching reviews: {e}")
        return {}

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
1. **MANDATORY**: ALWAYS start with an appropriate New Wash variant - this is the foundation of every haircare routine
2. Analyze the user's hair type, concerns, and needs from their input and conversation history
3. Consider their complete hair profile when making recommendations
4. Recommend New Wash first, then add 2-3 complementary products that work well with New Wash
5. Explain why New Wash is essential and why these products work together as a complete routine
6. Be warm, supportive, and educational
7. Include product URLs when recommending products
8. Reference specific details from the conversation to show you understand their needs
9. Make your response feel conversational and natural, not like a product catalog
10. Acknowledge their hair journey and be encouraging about their goals
11. Use their exact words when referencing what they've told you about their hair
12. You can suggest product combinations and routines based on the user's needs
13. Always explain how New Wash works as the foundation and how other products complement it

Please provide a personalized recommendation that feels like a friendly conversation with a haircare expert:"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))) 
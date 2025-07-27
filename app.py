from flask import Flask, request, jsonify, Response
import os
from scripts.pinecone_chatbot.hairstory_chatbot import (
    build_profile_with_function_call,
    query_pinecone,
    format_products_for_prompt,
    create_recommendation_prompt,
    profile_to_string,
    is_profile_complete,
    profile_fields,
    generate_next_question,
    map_user_input_to_field_value,
    client
)

app = Flask(__name__)

@app.route("/")
def home():
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hairstory Haircare Assistant</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f7f7f7; margin: 0; padding: 0; }
            .container { max-width: 500px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 24px; }
            h2 { text-align: center; color: #333; }
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

    # Use function calling to extract as much of the profile as possible with full context
    updated_profile = build_profile_with_function_call(
        conversation_history, 
        current_profile=user_profile
    )
    
    # Update the user profile with any new information
    user_profile.update(updated_profile)

    # Fallback: try mapping for the last user input if still missing fields
    if conversation_history:
        last_user_message = conversation_history[-1]["content"]
        missing_fields = [field for field, _ in profile_fields if not user_profile.get(field)]
        for field in missing_fields:
            mapped = map_user_input_to_field_value(field, last_user_message)
            if mapped:
                user_profile[field] = mapped

    if is_profile_complete(user_profile):
        profile_text = profile_to_string(user_profile)
        similar_products = query_pinecone(profile_text, top_k=5)
        formatted_products = format_products_for_prompt(similar_products)
        
        # Create recommendation prompt with full context
        prompt = create_recommendation_prompt(
            profile_text, 
            formatted_products, 
            conversation_history=conversation_history,
            user_profile=user_profile
        )
        
        # Call OpenAI to get the actual recommendation with full context
        openai_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a warm, knowledgeable haircare assistant for Hairstory. You help users find the perfect haircare routine based on their hair type and concerns. You have access to their complete conversation history and hair profile."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        recommendation = openai_response.choices[0].message.content
        response = {
            "profile": user_profile,
            "products": formatted_products,
            "recommendation": recommendation
        }
        return jsonify(response)
    else:
        # Generate a conversational question for the next missing field with full context
        ai_question = generate_next_question(user_profile, conversation_history)
        response = {
            "profile": user_profile,
            "message": ai_question or "Profile incomplete. Please provide more information."
        }
        return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))) 
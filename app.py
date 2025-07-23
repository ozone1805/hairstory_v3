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
            .msg { margin: 8px 0; }
            .user { color: #1a73e8; }
            .bot { color: #388e3c; }
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
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                const chat = document.getElementById('chat');
                const form = document.getElementById('input-area');
                const userInput = document.getElementById('user-input');
                const sendBtn = document.getElementById('send-btn');
                let conversation_history = [];
                let user_profile = {};

                function appendMessage(sender, text) {
                    const div = document.createElement('div');
                    div.className = 'msg ' + sender;
                    div.innerHTML = `<b>${sender === 'user' ? 'You' : 'Assistant'}:</b> ` + text.replace(/\\n/g, '<br>');
                    chat.appendChild(div);
                    chat.scrollTop = chat.scrollHeight;
                }

                // Show initial welcome message
                appendMessage('bot', "🌟 Welcome to Hairstory Haircare Assistant! 🌟<br>Let's get to know your hair so I can help you find the perfect products.");
                conversation_history.push({ role: 'assistant', content: "Welcome to Hairstory Haircare Assistant! Let's get to know your hair so I can help you find the perfect products." });

                form.addEventListener('submit', async function(e) {
                    e.preventDefault();
                    const text = userInput.value.trim();
                    if (!text) return;
                    appendMessage('user', text);
                    conversation_history.push({ role: 'user', content: text });
                    userInput.value = '';
                    userInput.disabled = true;
                    sendBtn.disabled = true;
                    appendMessage('bot', '<i>Thinking...</i>');
                    try {
                        const res = await fetch('/chat', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ conversation_history, user_profile })
                        });
                        if (!res.ok) {
                            throw new Error('Server error: ' + res.status);
                        }
                        const data = await res.json();
                        user_profile = data.profile || user_profile;
                        let reply = '';
                        if (data.recommendation) {
                            reply = data.recommendation;
                        } else if (data.products && data.products.length > 0) {
                            reply = "Here are some products you might like!";
                        } else if (data.message) {
                            reply = data.message;
                        } else {
                            reply = 'Sorry, I did not understand.';
                        }
                        // Remove the 'Thinking...' message
                        chat.removeChild(chat.lastChild);
                        appendMessage('bot', reply);
                    } catch (err) {
                        chat.removeChild(chat.lastChild);
                        appendMessage('bot', 'Error: ' + err.message);
                        console.error(err);
                    }
                    userInput.disabled = false;
                    sendBtn.disabled = false;
                    userInput.focus();
                });
            });
        </script>
    </body>
    </html>
    '''
    return Response(html, mimetype='text/html')

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    conversation_history = data.get("conversation_history", [])
    user_profile = data.get("user_profile", {})

    # Use function calling to extract as much of the profile as possible
    extracted = build_profile_with_function_call(
        [{"role": "system", "content": "You are a warm, friendly haircare assistant. You are building a hair profile for the user."}] + conversation_history
    )
    for field, _ in profile_fields:
        value = extracted.get(field, None)
        if value:
            user_profile[field] = value

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
        prompt = create_recommendation_prompt(profile_text, formatted_products)
        # Call OpenAI to get the actual recommendation
        openai_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a warm, knowledgeable haircare assistant for Hairstory. You help users find the perfect haircare routine based on their hair type and concerns."},
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
        # Generate a conversational question for the next missing field
        ai_question = generate_next_question(user_profile, conversation_history)
        response = {
            "profile": user_profile,
            "message": ai_question or "Profile incomplete. Please provide more information."
        }
        return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))) 
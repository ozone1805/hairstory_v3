from flask import Flask, request, jsonify
import os
from scripts.pinecone_chatbot.hairstory_chatbot import (
    build_profile_with_function_call,
    query_pinecone,
    format_products_for_prompt,
    create_recommendation_prompt,
    profile_to_string,
    is_profile_complete,
    profile_fields
)

app = Flask(__name__)

@app.route("/")
def home():
    return "Hairstory Haircare Assistant API is running!"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    conversation_history = data.get("conversation_history", [])
    user_profile = data.get("user_profile", {})

    # Build profile from conversation
    extracted = build_profile_with_function_call(
        [{"role": "system", "content": "You are a warm, friendly haircare assistant. You are building a hair profile for the user."}] + conversation_history
    )
    for field, _ in profile_fields:
        value = extracted.get(field, None)
        if value and not user_profile.get(field):
            user_profile[field] = value

    if is_profile_complete(user_profile):
        profile_text = profile_to_string(user_profile)
        similar_products = query_pinecone(profile_text, top_k=5)
        formatted_products = format_products_for_prompt(similar_products)
        prompt = create_recommendation_prompt(profile_text, formatted_products)
        return jsonify({
            "profile": user_profile,
            "products": formatted_products,
            "prompt": prompt
        })
    else:
        return jsonify({
            "profile": user_profile,
            "message": "Profile incomplete. Please provide more information."
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))) 
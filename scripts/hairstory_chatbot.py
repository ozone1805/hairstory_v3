import os
import openai
from pinecone import Pinecone
import json

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

def chat_with_user():
    """Main chat function."""
    print("🌟 Welcome to Hairstory Haircare Assistant! 🌟")
    print("Tell me about your hair type, concerns, or what you're looking for.")
    print("Type 'quit' to exit.\n")
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("Thank you for using Hairstory Haircare Assistant! 💫")
            break
        
        if not user_input:
            print("Please tell me about your hair so I can help you!")
            continue
        
        print("\n🔍 Finding the perfect products for you...")
        
        try:
            # Query Pinecone for relevant products
            similar_products = query_pinecone(user_input, top_k=5)
            
            if not similar_products:
                print("I couldn't find any relevant products. Let me ask you some questions to better understand your hair type and concerns.")
                continue
            
            # Format products for the prompt
            formatted_products = format_products_for_prompt(similar_products)
            
            # Create recommendation prompt
            prompt = create_recommendation_prompt(user_input, formatted_products)
            
            # Get recommendation from OpenAI
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
            
        except Exception as e:
            print(f"❌ Sorry, I encountered an error: {str(e)}")
            print("Please try again or rephrase your question.\n")

if __name__ == "__main__":
    chat_with_user() 
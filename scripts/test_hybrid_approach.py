import os
import openai
from pinecone import Pinecone
import json
from typing import Dict, List
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        logger.info(f"✅ Generated embedding (dimensions: {len(response.data[0].embedding)})")
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

def create_system_instructions(catalog_summary: str) -> str:
    """Create system instructions with product catalog summary."""
    return f"""You are a warm, understanding haircare assistant for Hairstory. Your goal is to help users find the perfect haircare routine based on their needs.

COMPLETE PRODUCT CATALOG SUMMARY:
{catalog_summary}

INSTRUCTIONS:
1. Analyze the user's hair type, concerns, and needs from their input
2. Recommend specific products from the catalog above that would work best for them
3. Explain why these products are a good match for their hair type/concerns
4. Be warm, supportive, and educational
5. Only recommend products from the Hairstory catalog above
6. Include the product URLs when recommending products
7. You can suggest product combinations and routines based on the user's needs
8. Be specific about which products work best for different hair types and concerns

IMPORTANT: Always base your recommendations on the actual product data provided above."""

def create_recommendation_prompt(user_input: str, products: List[Dict]) -> str:
    """Create a prompt for the OpenAI API with user input and relevant products."""
    
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
    
    return f"""Please provide a personalized recommendation based on the user's needs:

USER'S INPUT: {user_input}

SEMANTICALLY RELEVANT PRODUCTS (ranked by similarity):
{products_text}

Please provide a personalized recommendation:"""

def get_hybrid_recommendation(user_input: str, products: List[Dict], catalog_summary: str):
    """Get a personalized recommendation using the hybrid approach."""
    
    # Create system instructions with catalog summary
    system_instructions = create_system_instructions(catalog_summary)
    
    # Create recommendation prompt with Pinecone results
    recommendation_prompt = create_recommendation_prompt(user_input, products)
    
    messages = [
        {"role": "system", "content": system_instructions},
        {"role": "user", "content": recommendation_prompt}
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=800,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"❌ Error getting recommendation: {e}")
        return f"Error: {e}"

def main():
    """Main test function."""
    print("🚀 Testing Hybrid Approach: Pinecone + Product Catalog Summary")
    print("=" * 70)
    
    # Load products data for catalog summary
    products = load_products_data()
    catalog_summary = create_product_catalog_summary(products)
    
    print(f"\n📋 Product Catalog Summary Created ({len(products)} products)")
    print("-" * 50)
    print(catalog_summary[:500] + "..." if len(catalog_summary) > 500 else catalog_summary)
    
    # Test cases
    test_cases = [
        "I have curly hair that gets really frizzy and I need something to help with moisture",
        "I have oily scalp and fine hair, what should I use?",
        "I want to repair damaged hair from bleaching",
        "I'm looking for a complete haircare routine for dry hair"
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}: {test_input}")
        print("-" * 70)
        
        # Query Pinecone for relevant products
        print("🔍 Querying Pinecone for relevant products...")
        pinecone_results = query_pinecone(test_input, top_k=3)
        relevant_products = format_products_for_prompt(pinecone_results)
        
        print(f"✅ Retrieved {len(relevant_products)} relevant products:")
        for j, product in enumerate(relevant_products, 1):
            print(f"   {j}. {product['name']} (Score: {product['similarity_score']:.3f})")
        
        # Get hybrid recommendation
        print("\n🤖 Generating hybrid recommendation...")
        recommendation = get_hybrid_recommendation(test_input, relevant_products, catalog_summary)
        print(f"💬 Recommendation:\n{recommendation}")
        print("\n" + "=" * 70)

if __name__ == "__main__":
    main() 
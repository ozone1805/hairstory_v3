import os
import json
import logging
import openai
from typing import List, Dict

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

def load_products_data():
    """Load products data from JSON file."""
    try:
        with open("data/all_products.json", "r") as f:
            products = json.load(f)
        logger.info(f"✅ Loaded {len(products)} products from data/all_products.json")
        return products
    except FileNotFoundError:
        logger.warning("⚠️ all_products.json not found, trying enhanced_products.json")
        try:
            with open("data/enhanced_products.json", "r") as f:
                products = json.load(f)
            logger.info(f"✅ Loaded {len(products)} products from data/enhanced_products.json")
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

def create_system_instructions(catalog_summary: str) -> str:
    """Create system instructions with product catalog summary."""
    return f"""You are a warm, understanding haircare assistant for Hairstory. Your goal is to help users find the perfect haircare routine based on their needs.

COMPLETE PRODUCT CATALOG SUMMARY:
{catalog_summary}

RECOMMENDATION GUIDELINES:
1. **Hair Type Matching**: Always match products to the user's specific hair type
   - Fine/Oily: New Wash Deep Clean, Powder, Root Lift
   - Dry/Thick: New Wash Rich, Hair Balm, Oil
   - Curly/Coily: Hair Balm, Oil, Undressed
   - Damaged: Bond Boost + Bond Serum combination
   - All Hair Types: New Wash Original, Primer

2. **Product Categories**: Understand when to recommend different types
   - Cleansing: Choose appropriate New Wash variant
   - Pre-Cleansing: Pre-Wash for buildup removal
   - Pre-Styling: Primer for heat protection
   - Styling: Products for texture, volume, definition
   - Damage Repair: Bond products for damaged hair
   - Color Maintenance: Color Boost products for color-treated hair
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

# Pinecone recommendation prompt function commented out for conversations-only approach
# def create_recommendation_prompt(user_input: str, products: List[Dict]) -> str:
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
#     return f"""Please provide a personalized recommendation based on the user's needs:
# 
# USER INPUT: {user_input}
# 
# SEMANTICALLY RELEVANT PRODUCTS (ranked by similarity):
# {products_text}
# 
# Please provide a personalized recommendation:"""

def create_conversations_only_prompt(user_input: str) -> str:
    """Create a prompt for conversations-only recommendations using full catalog knowledge."""
    
    return f"""Please provide a personalized recommendation based on the user's needs using your complete product knowledge:

USER INPUT: {user_input}

INSTRUCTIONS:
1. Analyze the user's hair type, concerns, and needs from their input
2. Recommend specific products from the Hairstory catalog that would work best for them
3. Explain why these products are a good match for their hair type/concerns
4. Be warm, supportive, and educational
5. Include product URLs when recommending products
6. Make your response feel conversational and natural, not like a product catalog
7. You can suggest product combinations and routines based on the user's needs

Please provide a personalized recommendation that feels like a friendly conversation with a haircare expert:"""

def get_conversations_only_recommendation(user_input: str, catalog_summary: str):
    """Get a personalized recommendation using the conversations-only approach."""
    
    # Create system instructions with catalog summary
    system_instructions = create_system_instructions(catalog_summary)
    
    # Create recommendation prompt for conversations-only approach
    recommendation_prompt = create_conversations_only_prompt(user_input)
    
    messages = [
        {"role": "system", "content": system_instructions},
        {"role": "user", "content": recommendation_prompt}
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=800,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"❌ Error getting recommendation: {e}")
        return f"Error: {e}"

# Pinecone hybrid approach commented out for conversations-only approach
# def get_hybrid_recommendation(user_input: str, products: List[Dict], catalog_summary: str):
#     """Get a personalized recommendation using the hybrid approach."""
#     
#     # Create system instructions with catalog summary
#     system_instructions = create_system_instructions(catalog_summary)
#     
#     # Create recommendation prompt with Pinecone results
#     recommendation_prompt = create_recommendation_prompt(user_input, products)
#     
#     messages = [
#         {"role": "system", "content": system_instructions},
#         {"role": "user", "content": recommendation_prompt}
#     ]
#     
#     try:
#         response = client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=messages,
#             max_tokens=800,
#             temperature=0.7
#         )
#         
#         return response.choices[0].message.content.strip()
#     
#     except Exception as e:
#         logger.error(f"❌ Error getting recommendation: {e}")
#         return f"Error: {e}"

def main():
    """Main test function."""
    print("🧪 Testing Conversations-Only Approach")
    print("=" * 50)
    
    # Load products data
    products = load_products_data()
    if not products:
        print("❌ No products loaded. Exiting.")
        return
    
    # Create catalog summary
    catalog_summary = create_product_catalog_summary(products)
    print(f"✅ Created catalog summary with {len(catalog_summary)} characters")
    
    # Test queries
    test_queries = [
        "I have curly hair that's always frizzy and dry",
        "My hair is fine and oily, I need volume",
        "I have damaged hair from bleaching, what should I use?",
        "I want to maintain my red hair color",
        "I have thick, straight hair that's hard to style"
    ]
    
    print("\n🔍 Testing Conversations-Only Recommendations:")
    print("-" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query}")
        print("-" * 30)
        
        # Get conversations-only recommendation
        recommendation = get_conversations_only_recommendation(query, catalog_summary)
        print(f"Recommendation: {recommendation}")
        
        # Pinecone hybrid approach commented out
        # print(f"\n{i}. Query: {query}")
        # print("-" * 30)
        # 
        # # Get Pinecone results
        # pinecone_results = query_pinecone(query, top_k=5)
        # relevant_products = format_products_for_prompt(pinecone_results)
        # 
        # print(f"Pinecone Results: {len(relevant_products)} products found")
        # for j, product in enumerate(relevant_products, 1):
        #     print(f"  {j}. {product['name']} (Score: {product['similarity_score']:.3f})")
        # 
        # # Get hybrid recommendation
        # hybrid_recommendation = get_hybrid_recommendation(query, relevant_products, catalog_summary)
        # print(f"Hybrid Recommendation: {hybrid_recommendation}")
        
        print("\n" + "=" * 50)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Test script for the conversations-only approach.
This script tests the chatbot without Pinecone to verify it works correctly.
"""

import os
import sys
import json
import logging
from typing import List, Dict

# Add the parent directory to the path so we can import from scripts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.hybrid_chatbot import (
    load_products_data,
    create_product_catalog_summary,
    create_system_instructions,
    client
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def test_conversations_only():
    """Test the conversations-only approach."""
    print("🧪 Testing Conversations-Only Approach")
    print("=" * 60)
    
    # Load products data
    print("📦 Loading products data...")
    products = load_products_data()
    if not products:
        print("❌ No products loaded. Exiting.")
        return
    
    print(f"✅ Loaded {len(products)} products")
    
    # Create catalog summary
    print("📋 Creating catalog summary...")
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
    
    print(f"\n🔍 Testing {len(test_queries)} queries with conversations-only approach:")
    print("-" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query}")
        print("-" * 40)
        
        # Get conversations-only recommendation
        recommendation = get_conversations_only_recommendation(query, catalog_summary)
        print(f"💬 Recommendation:\n{recommendation}")
        
        print("\n" + "=" * 60)

def test_latency():
    """Test the latency of the conversations-only approach."""
    print("\n⏱️ Testing Latency")
    print("=" * 40)
    
    # Load products data
    products = load_products_data()
    if not products:
        print("❌ No products loaded. Exiting.")
        return
    
    catalog_summary = create_product_catalog_summary(products)
    
    # Test query
    test_query = "I have curly hair that's always frizzy and dry"
    
    import time
    
    print(f"Testing query: {test_query}")
    print("Measuring response time...")
    
    start_time = time.time()
    recommendation = get_conversations_only_recommendation(test_query, catalog_summary)
    end_time = time.time()
    
    response_time = end_time - start_time
    
    print(f"✅ Response time: {response_time:.2f} seconds")
    print(f"💬 Recommendation length: {len(recommendation)} characters")
    print(f"📊 Characters per second: {len(recommendation) / response_time:.1f}")

if __name__ == "__main__":
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key and try again")
        sys.exit(1)
    
    # Run tests
    test_conversations_only()
    test_latency()
    
    print("\n🎉 Conversations-only approach test completed!")
    print("The system is ready to use without Pinecone.") 
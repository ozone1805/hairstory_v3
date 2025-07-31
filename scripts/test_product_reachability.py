#!/usr/bin/env python3
"""
Product Reachability Test for Hairstory Assistant

This script tests if every product in the Hairstory catalog can be reached
through the recommendation algorithm by simulating different user personas
and scenarios that should trigger specific product recommendations.

Usage:
    python scripts/test_product_reachability.py
"""

import json
import os
import sys
import time
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.hybrid_chatbot import (
    load_products_data,
    create_product_catalog_summary,
    create_system_instructions,
    client,
    set_debug_mode
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Disable debug mode for cleaner output
set_debug_mode(False)

@dataclass
class TestCase:
    """Represents a test case for product reachability."""
    product_name: str
    persona: str
    user_input: str
    conversation_history: List[Dict]
    expected_keywords: List[str]
    description: str

class ProductReachabilityTester:
    """Tests if all products in the catalog can be reached through recommendations."""
    
    def __init__(self):
        # Load enhanced product data
        try:
            with open('data/enhanced_products.json', 'r', encoding='utf-8') as f:
                self.products = json.load(f)
            logger.info("✅ Loaded enhanced product data")
        except FileNotFoundError:
            self.products = load_products_data()
            logger.info("⚠️  Enhanced data not found, using original data")
        
        self.catalog_summary = self.create_enhanced_catalog_summary()
        self.system_instructions = self.create_enhanced_system_instructions()
        self.results = []
        
        # Load all product names for tracking
        self.all_product_names = [product['name'] for product in self.products]
        logger.info(f"Loaded {len(self.all_product_names)} products for testing")
    
    def create_test_cases(self) -> List[TestCase]:
        """Create comprehensive test cases for each product."""
        test_cases = []
        
        # Test cases for each product with different personas
        test_cases.extend([
            # New Wash Products
            TestCase(
                product_name="New Wash Original",
                persona="New to Hairstory",
                user_input="I'm looking for a gentle cleanser that can replace my shampoo and conditioner. I have normal hair and want something simple.",
                conversation_history=[
                    {"role": "user", "content": "Hi, I'm new to Hairstory and want to try something gentle"},
                    {"role": "assistant", "content": "Welcome! I'd love to help you find the perfect Hairstory products. What's your hair type?"},
                    {"role": "user", "content": "I have normal hair, not too oily or dry"}
                ],
                expected_keywords=["New Wash Original", "gentle", "cleanser"],
                description="New user with normal hair looking for gentle cleansing"
            ),
            
            TestCase(
                product_name="New Wash Deep Clean",
                persona="Oily Hair Sufferer",
                user_input="My hair gets oily really fast and I need something stronger to clean it properly. I wash every other day but it still feels greasy.",
                conversation_history=[
                    {"role": "user", "content": "My hair is so oily, I need help"},
                    {"role": "assistant", "content": "I understand oily hair can be frustrating. How often do you wash?"},
                    {"role": "user", "content": "Every other day but it still feels greasy by the end of the day"}
                ],
                expected_keywords=["Deep Clean", "oily", "stronger"],
                description="User with oily hair needing stronger cleansing"
            ),
            
            TestCase(
                product_name="New Wash Rich",
                persona="Dry Hair User",
                user_input="My hair is very dry and thick. I need something that will really moisturize and nourish my hair without weighing it down.",
                conversation_history=[
                    {"role": "user", "content": "My hair is so dry and thick"},
                    {"role": "assistant", "content": "Dry, thick hair needs extra moisture. What's your current routine?"},
                    {"role": "user", "content": "I use regular shampoo and conditioner but my hair still feels dry"}
                ],
                expected_keywords=["Rich", "dry", "thick", "moisturize"],
                description="User with dry, thick hair needing extra moisture"
            ),
            
            # Pre-Wash
            TestCase(
                product_name="Pre-Wash",
                persona="Product Buildup Sufferer",
                user_input="I use a lot of styling products and feel like they build up on my scalp. I need something to really clean my scalp before washing.",
                conversation_history=[
                    {"role": "user", "content": "I use lots of styling products"},
                    {"role": "assistant", "content": "Product buildup can be a real issue. What styling products do you use?"},
                    {"role": "user", "content": "Hairspray, mousse, and dry shampoo - I feel like they build up"}
                ],
                expected_keywords=["Pre-Wash", "buildup", "scalp"],
                description="User with product buildup needing scalp purification"
            ),
            
            # Bond Products
            TestCase(
                product_name="Bond Boost for New Wash",
                persona="Damaged Hair User",
                user_input="I've been bleaching and coloring my hair for years and it's really damaged. I need something to repair the damage from the inside out.",
                conversation_history=[
                    {"role": "user", "content": "My hair is really damaged from bleaching"},
                    {"role": "assistant", "content": "Chemical damage can be tough. How long have you been bleaching?"},
                    {"role": "user", "content": "Years of bleaching and coloring - my hair is so damaged"}
                ],
                expected_keywords=["Bond Boost", "damage", "repair"],
                description="User with chemically damaged hair needing repair"
            ),
            
            TestCase(
                product_name="Bond Serum",
                persona="Heat Damage User",
                user_input="I use heat tools every day and my hair is getting damaged. I need a leave-in treatment that can repair damage and protect from heat.",
                conversation_history=[
                    {"role": "user", "content": "I use heat tools daily"},
                    {"role": "assistant", "content": "Daily heat styling can cause damage. What tools do you use?"},
                    {"role": "user", "content": "Blow dryer, flat iron, curling iron - my hair is getting damaged"}
                ],
                expected_keywords=["Bond Serum", "heat", "damage", "leave-in"],
                description="User with heat damage needing leave-in repair"
            ),
            
            # Styling Products
            TestCase(
                product_name="Hair Balm",
                persona="Curly Hair User",
                user_input="I have curly hair and I'm looking for something to define my curls and keep them moisturized. I prefer to air dry my hair.",
                conversation_history=[
                    {"role": "user", "content": "I have curly hair"},
                    {"role": "assistant", "content": "Curly hair needs special care. How do you usually style it?"},
                    {"role": "user", "content": "I air dry and want to define my curls without frizz"}
                ],
                expected_keywords=["Hair Balm", "curly", "define", "air dry"],
                description="Curly hair user wanting definition and moisture"
            ),
            
            TestCase(
                product_name="Oil",
                persona="Frizz Sufferer",
                user_input="My hair is so frizzy and I need something to smooth it and add shine. I want something lightweight that won't weigh down my hair.",
                conversation_history=[
                    {"role": "user", "content": "My hair is so frizzy"},
                    {"role": "assistant", "content": "Frizz can be frustrating. What's your hair texture?"},
                    {"role": "user", "content": "Medium texture but very frizzy, I need something lightweight"}
                ],
                expected_keywords=["Oil", "frizz", "smooth", "lightweight"],
                description="User with frizzy hair needing lightweight smoothing"
            ),
            
            TestCase(
                product_name="Undressed",
                persona="Beach Wave Enthusiast",
                user_input="I want to achieve those perfect beach waves without using sea salt spray that dries out my hair. I want texture without the damage.",
                conversation_history=[
                    {"role": "user", "content": "I want beach waves"},
                    {"role": "assistant", "content": "Beach waves are beautiful! Do you currently use salt sprays?"},
                    {"role": "user", "content": "Yes but they dry out my hair, I want texture without damage"}
                ],
                expected_keywords=["Undressed", "beach", "waves", "texture"],
                description="User wanting beach waves without salt damage"
            ),
            
            TestCase(
                product_name="Powder",
                persona="Volume Seeker",
                user_input="I have fine hair and need volume. I also need something to refresh my hair between washes since it gets oily quickly.",
                conversation_history=[
                    {"role": "user", "content": "I have fine hair and need volume"},
                    {"role": "assistant", "content": "Fine hair can be challenging. How often do you wash?"},
                    {"role": "user", "content": "Every other day but it gets oily and flat quickly"}
                ],
                expected_keywords=["Powder", "volume", "fine", "refresh"],
                description="Fine hair user needing volume and refresh"
            ),
            
            TestCase(
                product_name="Root Lift",
                persona="Flat Hair Sufferer",
                user_input="My hair is so flat at the roots and I need serious volume. I use heat tools so I need something that works with heat styling.",
                conversation_history=[
                    {"role": "user", "content": "My hair is so flat at the roots"},
                    {"role": "assistant", "content": "Flat roots can be frustrating. Do you use heat tools?"},
                    {"role": "user", "content": "Yes, I blow dry and use hot tools for volume"}
                ],
                expected_keywords=["Root Lift", "volume", "roots", "heat"],
                description="User with flat roots needing heat-activated volume"
            ),
            
            TestCase(
                product_name="Wax",
                persona="Texture Seeker",
                user_input="I want to add texture and definition to my hair. I need something with medium hold that I can use to style and shape my hair.",
                conversation_history=[
                    {"role": "user", "content": "I want to add texture to my hair"},
                    {"role": "assistant", "content": "Texture can add great dimension. What's your hair length?"},
                    {"role": "user", "content": "Medium length, I want definition and shape"}
                ],
                expected_keywords=["Wax", "texture", "definition", "medium hold"],
                description="User wanting texture and definition with medium hold"
            ),
            
            # Primer
            TestCase(
                product_name="Primer",
                persona="Heat Styling User",
                user_input="I use heat tools every day and need protection. I want something that will protect my hair from heat damage and make styling easier.",
                conversation_history=[
                    {"role": "user", "content": "I use heat tools daily"},
                    {"role": "assistant", "content": "Daily heat styling needs protection. What tools do you use?"},
                    {"role": "user", "content": "Blow dryer, flat iron - I need heat protection"}
                ],
                expected_keywords=["Primer", "heat", "protection", "styling"],
                description="Heat styling user needing protection and easier styling"
            ),
            
            # Color Products
            TestCase(
                product_name="Purple Color Boost",
                persona="Blonde Hair User",
                user_input="I have blonde hair that's starting to look brassy. I need something to neutralize the yellow tones and keep my blonde bright.",
                conversation_history=[
                    {"role": "user", "content": "I have blonde hair"},
                    {"role": "assistant", "content": "Blonde hair needs special care. What's your concern?"},
                    {"role": "user", "content": "It's getting brassy and yellow, I need to neutralize the tones"}
                ],
                expected_keywords=["Purple", "blonde", "brassy", "neutralize"],
                description="Blonde hair user needing to neutralize brassiness"
            ),
            
            TestCase(
                product_name="Blue Color Boost",
                persona="Brunette Hair User",
                user_input="I have brunette hair that's getting orange tones. I need something to neutralize the orange and keep my brown hair cool-toned.",
                conversation_history=[
                    {"role": "user", "content": "I have brunette hair"},
                    {"role": "assistant", "content": "Brunette hair can develop warm tones. What's happening?"},
                    {"role": "user", "content": "It's getting orange tones, I want to keep it cool"}
                ],
                expected_keywords=["Blue", "brunette", "orange", "cool"],
                description="Brunette hair user needing to neutralize orange tones"
            ),
            
            TestCase(
                product_name="Red Color Boost",
                persona="Red Hair User",
                user_input="I have red hair that's fading. I need something to boost the red tones and keep my color vibrant between salon visits.",
                conversation_history=[
                    {"role": "user", "content": "I have red hair"},
                    {"role": "assistant", "content": "Red hair is beautiful but can fade quickly. What's your concern?"},
                    {"role": "user", "content": "It's fading and I want to keep it vibrant"}
                ],
                expected_keywords=["Red", "fading", "vibrant", "boost"],
                description="Red hair user needing color boost and vibrancy"
            ),
            
            # Bundles and Methods
            TestCase(
                product_name="New Wash Method for All Hair Types",
                persona="Complete Routine Seeker",
                user_input="I want the New Wash Method for All Hair Types bundle. I'm new to Hairstory and want a complete starter kit that works for any hair type.",
                conversation_history=[
                    {"role": "user", "content": "I want to switch to Hairstory completely"},
                    {"role": "assistant", "content": "That's great! Are you looking for a complete starter kit?"},
                    {"role": "user", "content": "Yes, I want the New Wash Method for All Hair Types bundle"}
                ],
                expected_keywords=["Method", "All Hair Types", "bundle", "starter"],
                description="New user specifically asking for New Wash Method for All Hair Types bundle"
            ),
            
            TestCase(
                product_name="Damage Repair Method",
                persona="Severely Damaged Hair",
                user_input="My hair is severely damaged from years of bleaching and heat styling. I need a complete damage repair system that will restore my hair.",
                conversation_history=[
                    {"role": "user", "content": "My hair is severely damaged"},
                    {"role": "assistant", "content": "Severe damage needs intensive repair. What caused the damage?"},
                    {"role": "user", "content": "Years of bleaching and heat styling - I need serious repair"}
                ],
                expected_keywords=["Damage Repair", "severe", "repair", "system"],
                description="User with severely damaged hair needing complete repair system"
            ),
            
            # Accessories
            TestCase(
                product_name="Massaging Scalp Brush",
                persona="Scalp Health Focused",
                user_input="I want to improve my scalp health and make sure I'm really cleansing my scalp properly. I need a tool to help with scalp massage and cleansing.",
                conversation_history=[
                    {"role": "user", "content": "I want to improve my scalp health"},
                    {"role": "assistant", "content": "Scalp health is crucial. What's your current routine?"},
                    {"role": "user", "content": "I just use my hands, I want better scalp cleansing"}
                ],
                expected_keywords=["Scalp Brush", "scalp", "massage", "cleansing"],
                description="User wanting to improve scalp health and cleansing"
            ),
            
            TestCase(
                product_name="Travel Bottle",
                persona="Frequent Traveler",
                user_input="I travel a lot and need a way to take my Hairstory products with me. I need something that's TSA compliant and won't leak.",
                conversation_history=[
                    {"role": "user", "content": "I travel frequently"},
                    {"role": "assistant", "content": "Traveling with haircare can be tricky. What's your concern?"},
                    {"role": "user", "content": "I need TSA compliant bottles that won't leak"}
                ],
                expected_keywords=["Travel", "TSA", "bottle", "leak"],
                description="Frequent traveler needing TSA compliant travel solution"
            ),
            
            # Additional test cases for previously failing products
            TestCase(
                product_name="Bond Boost for New Wash",
                persona="Severely Damaged Hair",
                user_input="I have severely damaged hair from years of bleaching and chemical treatments. I need something that can repair the damage from the inside out, not just a leave-in treatment.",
                conversation_history=[
                    {"role": "user", "content": "My hair is severely damaged from bleaching"},
                    {"role": "assistant", "content": "Severe damage needs intensive repair. What type of damage?"},
                    {"role": "user", "content": "Chemical damage from bleaching and coloring - I need something that repairs bonds"}
                ],
                expected_keywords=["Bond Boost", "damage", "repair", "bonds"],
                description="User with severe chemical damage needing bond repair"
            ),
            
            TestCase(
                product_name="New Wash Original 8oz Refill",
                persona="Cost-Conscious User",
                user_input="I love New Wash Original but I want to save money. Do you have a refill option that's more cost-effective?",
                conversation_history=[
                    {"role": "user", "content": "I use New Wash Original regularly"},
                    {"role": "assistant", "content": "That's great! Are you looking to save money?"},
                    {"role": "user", "content": "Yes, I want a refill option to save money"}
                ],
                expected_keywords=["Refill", "cost", "save", "money"],
                description="Cost-conscious user wanting refill option"
            ),
            
            TestCase(
                product_name="Richest Damage Repair Method",
                persona="Premium Damage Repair",
                user_input="I have extremely damaged hair and want the most comprehensive damage repair system available. Money is not an issue, I want the best possible treatment.",
                conversation_history=[
                    {"role": "user", "content": "I have extremely damaged hair"},
                    {"role": "assistant", "content": "Extreme damage needs intensive treatment. What's your budget?"},
                    {"role": "user", "content": "I want the best possible treatment, money is not an issue"}
                ],
                expected_keywords=["Richest", "premium", "damage", "repair"],
                description="Premium user wanting maximum damage repair"
            ),
            
            TestCase(
                product_name="New Wash Dispenser with Pump",
                persona="Convenience Seeker",
                user_input="I use New Wash regularly and want a more convenient way to dispense it. I need something with a pump that makes application easier.",
                conversation_history=[
                    {"role": "user", "content": "I use New Wash regularly"},
                    {"role": "assistant", "content": "Great! Are you looking for convenience improvements?"},
                    {"role": "user", "content": "Yes, I want easier application with a pump"}
                ],
                expected_keywords=["Dispenser", "pump", "convenient", "application"],
                description="Regular user wanting convenient application"
            ),
            
            # Additional test cases for bundle, refill, and premium products
            TestCase(
                product_name="Care and Texture Set",
                persona="Texture Enthusiast",
                user_input="I want to create texture and definition in my hair. I'm looking for a complete styling routine that includes products for texture and definition.",
                conversation_history=[
                    {"role": "user", "content": "I want to add texture to my hair"},
                    {"role": "assistant", "content": "Texture can add great dimension. Are you looking for a complete routine?"},
                    {"role": "user", "content": "Yes, I want a complete styling bundle for texture"}
                ],
                expected_keywords=["Care", "Texture", "Set", "bundle", "styling"],
                description="User wanting complete texture styling bundle"
            ),
            
            TestCase(
                product_name="Clarifying Hair Method",
                persona="Buildup Sufferer",
                user_input="I have a lot of product buildup and need a complete clarifying system to reset my hair. I want everything I need to remove buildup.",
                conversation_history=[
                    {"role": "user", "content": "I have product buildup"},
                    {"role": "assistant", "content": "Buildup can be frustrating. Do you want a complete system?"},
                    {"role": "user", "content": "Yes, I want a complete clarifying bundle"}
                ],
                expected_keywords=["Clarifying", "Method", "bundle", "buildup"],
                description="User wanting complete clarifying bundle"
            ),
            
            TestCase(
                product_name="New Wash Method for Oily Hair",
                persona="Oily Hair Bundle Seeker",
                user_input="I have oily hair and want a complete routine specifically designed for oily hair. I want everything I need in one bundle.",
                conversation_history=[
                    {"role": "user", "content": "I have oily hair"},
                    {"role": "assistant", "content": "Oily hair needs special care. Do you want a complete routine?"},
                    {"role": "user", "content": "Yes, I want a complete bundle for oily hair"}
                ],
                expected_keywords=["Method", "Oily", "bundle", "complete"],
                description="User wanting complete oily hair bundle"
            ),
            
            TestCase(
                product_name="New Wash Method for Dry Hair",
                persona="Dry Hair Bundle Seeker",
                user_input="I have dry hair and want a complete routine specifically designed for dry hair. I want everything I need in one bundle.",
                conversation_history=[
                    {"role": "user", "content": "I have dry hair"},
                    {"role": "assistant", "content": "Dry hair needs extra moisture. Do you want a complete routine?"},
                    {"role": "user", "content": "Yes, I want a complete bundle for dry hair"}
                ],
                expected_keywords=["Method", "Dry", "bundle", "complete"],
                description="User wanting complete dry hair bundle"
            ),
            
            TestCase(
                product_name="Healthiest Hair Method",
                persona="Premium Care Seeker",
                user_input="I want the Healthiest Hair Method bundle. I'm looking for a complete system that focuses on optimal hair health and I'm willing to invest in the best care.",
                conversation_history=[
                    {"role": "user", "content": "I want the best haircare for hair health"},
                    {"role": "assistant", "content": "Hair health is important. Are you looking for a specific system?"},
                    {"role": "user", "content": "Yes, I want the Healthiest Hair Method bundle"}
                ],
                expected_keywords=["Healthiest", "Method", "bundle", "health"],
                description="Premium user specifically asking for Healthiest Hair Method bundle"
            ),
            
            TestCase(
                product_name="Richest Hair Method",
                persona="Ultimate Premium Seeker",
                user_input="I want the most comprehensive haircare system available. I want everything Hairstory has to offer for maximum benefits.",
                conversation_history=[
                    {"role": "user", "content": "I want the most comprehensive system"},
                    {"role": "assistant", "content": "That's ambitious! What's your goal?"},
                    {"role": "user", "content": "I want the ultimate system with maximum benefits"}
                ],
                expected_keywords=["Richest", "Method", "ultimate", "maximum"],
                description="User wanting ultimate comprehensive system"
            ),
            
            # Additional test cases for remaining products
            TestCase(
                product_name="New Wash Original Trial Kit",
                persona="Cautious New User",
                user_input="I want to try Hairstory but I'm not sure if it will work for me. I want to test it first before committing to full-size products.",
                conversation_history=[
                    {"role": "user", "content": "I want to try Hairstory"},
                    {"role": "assistant", "content": "That's great! Are you looking to test first?"},
                    {"role": "user", "content": "Yes, I want to try it before committing to full products"}
                ],
                expected_keywords=["Trial", "Kit", "test", "commit"],
                description="Cautious user wanting to test before committing"
            ),
            
            TestCase(
                product_name="New Wash Deep Clean 8oz Refill",
                persona="Oily Hair Refill User",
                user_input="I use New Wash Deep Clean regularly and want to save money. Do you have a refill option for the Deep Clean formula?",
                conversation_history=[
                    {"role": "user", "content": "I use New Wash Deep Clean regularly"},
                    {"role": "assistant", "content": "Great! Are you looking to save money?"},
                    {"role": "user", "content": "Yes, I want a refill option for Deep Clean"}
                ],
                expected_keywords=["Deep Clean", "Refill", "save", "money"],
                description="Regular Deep Clean user wanting refill option"
            ),
            
            TestCase(
                product_name="New Wash Rich 8oz Refill",
                persona="Dry Hair Refill User",
                user_input="I use New Wash Rich regularly and want to save money. Do you have a refill option for the Rich formula?",
                conversation_history=[
                    {"role": "user", "content": "I use New Wash Rich regularly"},
                    {"role": "assistant", "content": "Great! Are you looking to save money?"},
                    {"role": "user", "content": "Yes, I want a refill option for Rich"}
                ],
                expected_keywords=["Rich", "Refill", "save", "money"],
                description="Regular Rich user wanting refill option"
            ),
        ])
        
        return test_cases
    
    def create_enhanced_catalog_summary(self) -> str:
        """Create an enhanced catalog summary with categories and better descriptions."""
        summary_parts = []
        
        # Group products by category
        categories = {}
        for product in self.products:
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
                
                # Add enhanced description
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
        
        return "\n".join(summary_parts)
    
    def create_enhanced_system_instructions(self) -> str:
        """Create enhanced system instructions with better product understanding."""
        return f"""You are a warm, understanding haircare assistant for Hairstory. Your goal is to help users find the perfect haircare routine based on their needs.

COMPLETE PRODUCT CATALOG WITH ENHANCED INFORMATION:
{self.catalog_summary}

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

IMPORTANT: Base all recommendations on the enhanced product data above. Consider hair type, use case, and product category when making recommendations."""
    
    def run_single_test(self, test_case: TestCase) -> Dict:
        """Run a single test case and return results."""
        logger.info(f"Testing: {test_case.product_name} - {test_case.description}")
        
        try:
            # Create a simple prompt that focuses on the user's needs
            prompt = f"""Based on the user's needs, recommend the most appropriate Hairstory products.

USER'S NEEDS: {test_case.user_input}

CONVERSATION CONTEXT:
{chr(10).join([f"{msg['role'].title()}: {msg['content']}" for msg in test_case.conversation_history])}

AVAILABLE PRODUCTS:
{self.catalog_summary}

Please recommend specific products that would best address the user's needs. Be specific about product names and explain why each product is a good match.

Recommendation:"""
            
            # Get recommendation from LLM
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_instructions},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.7
            )
            
            recommendation = response.choices[0].message.content
            
            # Check if the target product was recommended
            target_product_found = test_case.product_name.lower() in recommendation.lower()
            
            # Check for expected keywords
            keywords_found = []
            for keyword in test_case.expected_keywords:
                if keyword.lower() in recommendation.lower():
                    keywords_found.append(keyword)
            
            # Get all products mentioned in the recommendation
            mentioned_products = []
            for product in self.all_product_names:
                if product.lower() in recommendation.lower():
                    mentioned_products.append(product)
            
            result = {
                "test_case": test_case,
                "target_product_found": target_product_found,
                "keywords_found": keywords_found,
                "keywords_missing": [k for k in test_case.expected_keywords if k not in keywords_found],
                "mentioned_products": mentioned_products,
                "recommendation": recommendation,
                "success": target_product_found
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error testing {test_case.product_name}: {e}")
            return {
                "test_case": test_case,
                "target_product_found": False,
                "keywords_found": [],
                "keywords_missing": test_case.expected_keywords,
                "mentioned_products": [],
                "recommendation": f"Error: {str(e)}",
                "success": False,
                "error": str(e)
            }
    
    def run_all_tests(self) -> Dict:
        """Run all test cases and compile results."""
        test_cases = self.create_test_cases()
        logger.info(f"Running {len(test_cases)} test cases...")
        
        results = []
        successful_tests = 0
        failed_tests = 0
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"Progress: {i}/{len(test_cases)} - Testing {test_case.product_name}")
            
            result = self.run_single_test(test_case)
            results.append(result)
            
            if result["success"]:
                successful_tests += 1
                logger.info(f"✅ PASS: {test_case.product_name}")
            else:
                failed_tests += 1
                logger.warning(f"❌ FAIL: {test_case.product_name}")
            
            # Small delay to avoid rate limiting
            time.sleep(1)
        
        # Compile summary
        summary = {
            "total_tests": len(test_cases),
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": successful_tests / len(test_cases) * 100,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        return summary
    
    def generate_report(self, summary: Dict) -> str:
        """Generate a detailed report of the test results."""
        report = []
        report.append("=" * 80)
        report.append("HAIRSTORY PRODUCT REACHABILITY TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {summary['timestamp']}")
        report.append(f"Total Tests: {summary['total_tests']}")
        report.append(f"Successful: {summary['successful_tests']}")
        report.append(f"Failed: {summary['failed_tests']}")
        report.append(f"Success Rate: {summary['success_rate']:.1f}%")
        report.append("")
        
        # Group results by success/failure
        successful_results = [r for r in summary['results'] if r['success']]
        failed_results = [r for r in summary['results'] if not r['success']]
        
        if successful_results:
            report.append("✅ SUCCESSFUL TESTS:")
            report.append("-" * 40)
            for result in successful_results:
                test_case = result['test_case']
                report.append(f"• {test_case.product_name}")
                report.append(f"  Persona: {test_case.persona}")
                report.append(f"  Keywords Found: {', '.join(result['keywords_found'])}")
                report.append("")
        
        if failed_results:
            report.append("❌ FAILED TESTS:")
            report.append("-" * 40)
            for result in failed_results:
                test_case = result['test_case']
                report.append(f"• {test_case.product_name}")
                report.append(f"  Persona: {test_case.persona}")
                report.append(f"  Missing Keywords: {', '.join(result['keywords_missing'])}")
                report.append(f"  Mentioned Products: {', '.join(result['mentioned_products'][:3])}...")
                report.append("")
        
        # Product coverage analysis
        all_mentioned_products = set()
        for result in summary['results']:
            all_mentioned_products.update(result['mentioned_products'])
        
        missing_products = set(self.all_product_names) - all_mentioned_products
        
        report.append("📊 PRODUCT COVERAGE ANALYSIS:")
        report.append("-" * 40)
        report.append(f"Total Products in Catalog: {len(self.all_product_names)}")
        report.append(f"Products Mentioned in Tests: {len(all_mentioned_products)}")
        report.append(f"Products Never Mentioned: {len(missing_products)}")
        report.append(f"Coverage Rate: {len(all_mentioned_products) / len(self.all_product_names) * 100:.1f}%")
        
        if missing_products:
            report.append("")
            report.append("🚨 PRODUCTS NEVER RECOMMENDED:")
            for product in sorted(missing_products):
                report.append(f"• {product}")
        
        return "\n".join(report)
    
    def save_results(self, summary: Dict, filename: str = None):
        """Save test results to a file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"product_reachability_test_{timestamp}.json"
        
        # Save detailed results
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        # Save human-readable report
        report_filename = filename.replace('.json', '_report.txt')
        report = self.generate_report(summary)
        with open(report_filename, 'w') as f:
            f.write(report)
        
        logger.info(f"Results saved to {filename}")
        logger.info(f"Report saved to {report_filename}")
        
        return filename, report_filename

def main():
    """Main function to run the product reachability tests."""
    print("🚀 Starting Hairstory Product Reachability Tests...")
    print("This will test if every product can be reached through recommendations.")
    print("=" * 80)
    
    try:
        # Initialize tester
        tester = ProductReachabilityTester()
        
        # Run all tests
        summary = tester.run_all_tests()
        
        # Generate and display report
        report = tester.generate_report(summary)
        print(report)
        
        # Save results
        json_file, report_file = tester.save_results(summary)
        
        print(f"\n📁 Results saved to:")
        print(f"   JSON: {json_file}")
        print(f"   Report: {report_file}")
        
        # Final assessment
        if summary['success_rate'] >= 80:
            print(f"\n🎉 EXCELLENT: {summary['success_rate']:.1f}% success rate!")
        elif summary['success_rate'] >= 60:
            print(f"\n👍 GOOD: {summary['success_rate']:.1f}% success rate")
        else:
            print(f"\n⚠️  NEEDS IMPROVEMENT: {summary['success_rate']:.1f}% success rate")
            print("Consider improving the recommendation algorithm or product data.")
        
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Enhance Product Data for Better Recommendations

This script enhances the product data with:
1. Better product categories
2. Improved descriptions with hair type compatibility
3. Use case information
4. Product relationships
"""

import json
import os
from typing import Dict, List

def enhance_product_data():
    """Enhance the product data with better categories and descriptions."""
    
    # Load current product data
    with open('data/all_products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    # Define product categories and enhancements
    product_enhancements = {
        "New Wash Method for All Hair Types": {
            "category": "starter_bundle",
            "hair_types": ["all"],
            "use_cases": ["new_to_hairstory", "complete_routine", "starter_kit"],
            "enhanced_description": "COMPLETE STARTER KIT: Everything you need to begin your Hairstory journey. Includes Pre-Wash for scalp purification, New Wash Original for gentle cleansing, and Massaging Scalp Brush for effective application. Perfect for anyone new to Hairstory or wanting a complete routine. This bundle saves money compared to buying products individually."
        },
        "New Wash Original": {
            "category": "cleansing",
            "hair_types": ["all", "normal", "balanced"],
            "use_cases": ["daily_cleansing", "gentle_cleansing"],
            "enhanced_description": "Gentle cleansing cream that replaces shampoo and conditioner. Suitable for all hair types, especially normal to balanced hair. Detergent-free formula that cleanses while conditioning and nourishing."
        },
        "New Wash Original 8oz Refill": {
            "category": "cleansing_refill",
            "hair_types": ["all", "normal", "balanced"],
            "use_cases": ["refill", "cost_savings", "eco_friendly", "regular_user"],
            "enhanced_description": "REFILL PACK - COST SAVINGS: Same New Wash Original formula in a cost-effective refill format. Perfect for regular users who want to save money and reduce packaging waste. More affordable than buying full bottles repeatedly."
        },
        "Pre-Wash": {
            "category": "pre_cleansing",
            "hair_types": ["all", "oily", "product_buildup"],
            "use_cases": ["scalp_cleansing", "buildup_removal", "transition"],
            "enhanced_description": "Prebiotic micellar scalp rinse that purifies the scalp and removes product buildup. Use before New Wash for deeper cleansing. Ideal for oily hair, product buildup, or transitioning from traditional shampoo."
        },
        "Primer": {
            "category": "pre_styling",
            "hair_types": ["all"],
            "use_cases": ["heat_protection", "pre_styling", "moisture"],
            "enhanced_description": "Weightless leave-in mist with heat protection up to 450°F. Provides moisture, detangles, and protects from heat, humidity, and UV damage. Essential for anyone using heat tools."
        },
        "New Wash Deep Clean": {
            "category": "cleansing",
            "hair_types": ["fine", "oily", "greasy"],
            "use_cases": ["stronger_cleansing", "oily_hair"],
            "enhanced_description": "Stronger cleansing formula with apple cider vinegar for fine and oily hair. Removes excess oil and buildup more effectively than Original. Perfect for hair that gets greasy quickly."
        },
        "Bond Boost for New Wash": {
            "category": "damage_repair",
            "hair_types": ["damaged", "chemically_treated", "bleached"],
            "use_cases": ["damage_repair", "chemical_damage", "bond_repair"],
            "enhanced_description": "Intensive damage repair treatment that must be mixed with New Wash. Uses ProTarget Technology to repair disulfide bonds damaged by chemical treatments. For severely damaged hair from bleaching, coloring, or heat styling."
        },
        "Bond Serum": {
            "category": "damage_repair",
            "hair_types": ["damaged", "chemically_treated", "heat_damaged"],
            "use_cases": ["leave_in_repair", "heat_protection", "damage_repair"],
            "enhanced_description": "Leave-in damage repair treatment with heat protection up to 450°F. Repairs bonds and provides ongoing protection. Use after Bond Boost for maximum repair benefits."
        },
        "New Wash Rich 8oz Refill": {
            "category": "cleansing_refill",
            "hair_types": ["dry", "thick", "coarse"],
            "use_cases": ["refill", "dry_hair", "cost_savings", "eco_friendly", "regular_user"],
            "enhanced_description": "REFILL PACK - DRY HAIR: Same New Wash Rich formula in a cost-effective refill format. Extra moisturizing for dry and thick hair. Perfect for regular users who need more moisture and want to save money."
        },
        "New Wash Deep Clean 8oz Refill": {
            "category": "cleansing_refill",
            "hair_types": ["fine", "oily"],
            "use_cases": ["refill", "oily_hair", "cost_savings", "eco_friendly", "regular_user"],
            "enhanced_description": "REFILL PACK - OILY HAIR: Same New Wash Deep Clean formula in a cost-effective refill format. Stronger cleansing for fine and oily hair. Perfect for regular users who need deeper cleansing and want to save money."
        },
        "New Wash Original Trial Kit": {
            "category": "starter_bundle",
            "hair_types": ["all"],
            "use_cases": ["trial", "new_to_hairstory", "travel", "risk_free"],
            "enhanced_description": "TRIAL KIT - RISK-FREE START: Perfect for trying Hairstory before committing. Includes 3oz New Wash Original, reusable tin, Massaging Scalp Brush, and $20 voucher. Great for new users who want to test the system without full commitment. Risk-free way to experience Hairstory."
        },
        "Hair Balm": {
            "category": "styling",
            "hair_types": ["curly", "wavy", "dry", "frizzy"],
            "use_cases": ["air_dry", "curl_definition", "moisture", "frizz_control"],
            "enhanced_description": "Air-dry lotion for defining curls and waves while providing moisture. Reduces frizz and enhances natural texture. Perfect for curly and wavy hair that needs definition without heat."
        },
        "Oil": {
            "category": "styling",
            "hair_types": ["all", "frizzy", "dry"],
            "use_cases": ["shine", "frizz_control", "moisture", "finishing"],
            "enhanced_description": "Lightweight nourishing oil with 8 essential oils. Adds shine, reduces frizz, and moisturizes without weighing hair down. Perfect for all hair types needing shine and frizz control."
        },
        "Undressed": {
            "category": "styling",
            "hair_types": ["all", "wavy", "straight"],
            "use_cases": ["beach_waves", "texture", "volume"],
            "enhanced_description": "Salt-free texturizing spray for beach waves without damage. Creates touchable texture and waves while protecting from UV rays. Perfect for achieving beachy waves without the drying effects of sea salt."
        },
        "Powder": {
            "category": "styling",
            "hair_types": ["fine", "thin", "oily"],
            "use_cases": ["volume", "dry_shampoo", "refresh", "oil_absorption"],
            "enhanced_description": "Non-aerosol dry shampoo that absorbs oil and adds volume. Talc-free formula that refreshes hair between washes. Perfect for fine hair needing volume and oil control."
        },
        "New Wash Rich": {
            "category": "cleansing",
            "hair_types": ["dry", "thick", "coarse"],
            "use_cases": ["dry_hair", "moisture", "thick_hair"],
            "enhanced_description": "Extra moisturizing cleansing cream for dry and thick hair. Provides more hydration than Original while still cleansing effectively. Ideal for hair that needs extra moisture."
        },
        "Root Lift": {
            "category": "styling",
            "hair_types": ["fine", "thin", "flat"],
            "use_cases": ["volume", "heat_styling", "root_lift"],
            "enhanced_description": "Heat-activated volumizing spray that lifts hair at the roots. Works with heat tools to create lasting volume. Perfect for fine hair that needs serious volume boost."
        },
        "Wax": {
            "category": "styling",
            "hair_types": ["all", "short", "medium"],
            "use_cases": ["texture", "definition", "hold", "shaping"],
            "enhanced_description": "Medium-hold wax for adding texture and definition. Flexible formula that shapes hair without feeling sticky. Great for creating texture and definition in short to medium hair."
        },
        "Purple Color Boost": {
            "category": "color_maintenance",
            "hair_types": ["blonde", "gray", "silver"],
            "use_cases": ["brass_neutralization", "color_maintenance", "tone_correction"],
            "enhanced_description": "Purple color treatment to neutralize yellow and brassy tones in blonde hair. Maintains cool, bright blonde color between salon visits. Essential for keeping blonde hair from turning brassy."
        },
        "Blue Color Boost": {
            "category": "color_maintenance",
            "hair_types": ["brunette", "brown"],
            "use_cases": ["orange_neutralization", "color_maintenance", "tone_correction"],
            "enhanced_description": "Blue color treatment to neutralize orange tones in brunette hair. Keeps brown hair cool-toned and prevents warm, orange undertones. Perfect for maintaining cool brunette color."
        },
        "Red Color Boost": {
            "category": "color_maintenance",
            "hair_types": ["red", "auburn"],
            "use_cases": ["color_vibrancy", "color_maintenance", "fade_prevention"],
            "enhanced_description": "Red color treatment to boost and maintain vibrant red tones. Prevents fading and keeps red hair bright between salon visits. Essential for maintaining vibrant red color."
        },
        "New Wash Method for Oily Hair": {
            "category": "starter_bundle",
            "hair_types": ["oily", "fine"],
            "use_cases": ["oily_hair_routine", "complete_routine"],
            "enhanced_description": "Complete routine for oily hair. Includes Pre-Wash for scalp purification, New Wash Deep Clean for stronger cleansing, and Massaging Scalp Brush. Perfect for fine, oily hair that needs extra cleansing power."
        },
        "New Wash Method for Dry Hair": {
            "category": "starter_bundle",
            "hair_types": ["dry", "thick"],
            "use_cases": ["dry_hair_routine", "complete_routine", "moisture_focused"],
            "enhanced_description": "DRY HAIR BUNDLE - MOISTURE FOCUSED: Complete routine specifically designed for dry hair. Includes Pre-Wash for scalp health, New Wash Rich for extra moisture, and Massaging Scalp Brush. Perfect for dry, thick hair that needs extra hydration. Complete system for dry hair care."
        },
        "Care and Texture Set": {
            "category": "styling_bundle",
            "hair_types": ["all"],
            "use_cases": ["styling_routine", "texture_creation", "bundle_savings"],
            "enhanced_description": "STYLING BUNDLE - TEXTURE & DEFINITION: Complete styling routine for creating texture and definition. Includes Hair Balm for moisture and definition, and Undressed for beach waves. Perfect for anyone wanting to enhance their hair's natural texture. Bundle saves money compared to buying products separately."
        },
        "Massaging Scalp Brush": {
            "category": "accessory",
            "hair_types": ["all"],
            "use_cases": ["scalp_health", "product_application", "cleansing"],
            "enhanced_description": "Silicone scalp brush for effective product application and scalp massage. Soft bristles soothe scalp while removing impurities. Essential tool for proper New Wash application and scalp health."
        },
        "Travel Bottle": {
            "category": "accessory",
            "hair_types": ["all"],
            "use_cases": ["travel", "portability", "tsa_compliant"],
            "enhanced_description": "TSA-compliant travel bottle for taking Hairstory products on the go. Leak-proof design perfect for travel. Essential for anyone who travels frequently and wants to maintain their haircare routine."
        },
        "Damage Repair Method": {
            "category": "damage_repair_bundle",
            "hair_types": ["damaged", "chemically_treated"],
            "use_cases": ["damage_repair", "complete_repair_routine"],
            "enhanced_description": "Complete damage repair system. Includes Bond Boost for intensive repair, Bond Serum for ongoing protection, and Massaging Scalp Brush. Perfect for severely damaged hair needing comprehensive repair."
        },
        "Richest Damage Repair Method": {
            "category": "premium_damage_repair_bundle",
            "hair_types": ["severely_damaged", "chemically_treated"],
            "use_cases": ["intensive_repair", "premium_routine", "maximum_repair"],
            "enhanced_description": "PREMIUM DAMAGE REPAIR BUNDLE - MAXIMUM REPAIR: Ultimate damage repair system with maximum repair benefits. Includes all damage repair products plus additional treatments for severely damaged hair. Premium solution for hair that needs intensive repair. Most comprehensive repair system available."
        },
        "Healthiest Hair Method": {
            "category": "premium_bundle",
            "hair_types": ["all"],
            "use_cases": ["premium_routine", "complete_care", "comprehensive_system", "optimal_health"],
            "enhanced_description": "HEALTHIEST HAIR METHOD - OPTIMAL HEALTH BUNDLE: Premium complete haircare system designed for optimal hair health. Includes all essential products for a comprehensive routine that promotes the healthiest possible hair. Perfect for anyone wanting the complete Hairstory experience with premium care focused on hair health."
        },
        "Richest Hair Method": {
            "category": "premium_bundle",
            "hair_types": ["all"],
            "use_cases": ["premium_routine", "maximum_benefits", "ultimate_system"],
            "enhanced_description": "ULTIMATE PREMIUM BUNDLE - MAXIMUM BENEFITS: Ultimate premium haircare system with maximum benefits. Includes all products for the most comprehensive routine. Perfect for those wanting the complete Hairstory experience with all available products. Most comprehensive system available."
        },
        "Clarifying Hair Method": {
            "category": "clarifying_bundle",
            "hair_types": ["all", "buildup"],
            "use_cases": ["clarifying", "buildup_removal", "reset", "bundle_savings"],
            "enhanced_description": "CLARIFYING BUNDLE - BUILDUP REMOVAL: Complete clarifying system for removing buildup and resetting hair. Includes Pre-Wash for deep cleansing and clarifying treatments. Perfect for hair with product buildup or needing a fresh start. Bundle saves money compared to buying products separately."
        },
        "New Wash Dispenser with Pump": {
            "category": "accessory",
            "hair_types": ["all"],
            "use_cases": ["convenience", "easy_application", "storage"],
            "enhanced_description": "Convenient dispenser with pump for easy New Wash application. 32oz capacity perfect for regular users. Makes application easier and more controlled."
        }
    }
    
    # Enhance each product
    enhanced_products = []
    for product in products:
        product_name = product["name"]
        enhancement = product_enhancements.get(product_name, {})
        
        # Create enhanced product
        enhanced_product = {
            **product,
            "category": enhancement.get("category", "other"),
            "hair_types": enhancement.get("hair_types", ["all"]),
            "use_cases": enhancement.get("use_cases", []),
            "enhanced_description": enhancement.get("enhanced_description", product.get("details", product.get("subtitle", ""))),
            "product_type": product.get("type", "singleton")
        }
        
        # Add hair type compatibility to description if not already present
        if "hair_types" in enhancement and enhancement["hair_types"] != ["all"]:
            hair_type_text = f"Best for: {', '.join(enhancement['hair_types'])} hair. "
            if not enhanced_product["enhanced_description"].startswith(hair_type_text):
                enhanced_product["enhanced_description"] = hair_type_text + enhanced_product["enhanced_description"]
        
        enhanced_products.append(enhanced_product)
    
    # Save enhanced data
    with open('data/enhanced_products.json', 'w', encoding='utf-8') as f:
        json.dump(enhanced_products, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Enhanced {len(enhanced_products)} products")
    print("📁 Saved to: data/enhanced_products.json")
    
    # Print summary of categories
    categories = {}
    for product in enhanced_products:
        cat = product["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\n📊 Product Categories:")
    for category, count in sorted(categories.items()):
        print(f"  {category}: {count} products")
    
    return enhanced_products

if __name__ == "__main__":
    enhance_product_data() 
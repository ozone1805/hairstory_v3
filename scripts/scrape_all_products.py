import csv
import requests
from bs4 import BeautifulSoup
import json
import time
import sys
import re

def classify_product_type(product_name, soup):
    """
    Classify the product type based on name and page content.
    
    Args:
        product_name (str): The product name
        soup (BeautifulSoup): Parsed HTML content
        
    Returns:
        str: Product type - "bundle" or "singleton"
    """
    # Check for bundle products using specific CSS selector for "set includes"
    if soup:
        set_includes_element = soup.select_one('button[content-type="set-includes"]')
        if set_includes_element:
            return "bundle"
    
    # Check for bundle products (Set or Method in name)
    if "Set" in product_name or "Method" in product_name:
        return "bundle"
    
    # Everything else is a singleton
    return "singleton"

def scrape_product_details(url, product_name):
    """
    Scrape product details from a Hairstory product page using the original logic.
    
    Args:
        url (str): The product URL to scrape
        product_name (str): The product name from CSV
        
    Returns:
        dict: Dictionary containing product information
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"Fetching: {product_name} - {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Use the original selectors (removed title as it only contains first word of product name)
        selectors = {
            "subtitle": "#MainContent h2",
            "details": "div#ProductDescription",
            "benefits": "div[content-type='benefit']",
            "how_to_use": "div[content-type='how_to_use']",
            "ingredients": "div[content-type='ingredients']"
        }
        
        # Extract text content
        results = {"name": product_name, "url": url}
        for key, selector in selectors.items():
            element = soup.select_one(selector)
            if element:
                text_content = element.get_text(strip=True)
                # Apply formatting fix to benefits field
                if key == "benefits":
                    text_content = fix_benefits_formatting(text_content)
                results[key] = text_content
            else:
                results[key] = None
        
        # Add product type classification
        results["type"] = classify_product_type(product_name, soup)
        
        # Extract set_includes for bundle products
        if results["type"] == "bundle":
            set_includes_div = soup.select_one('div[content-type="set-includes"]')
            if set_includes_div:
                set_includes_items = []
                li_elements = set_includes_div.find_all('li')
                for li in li_elements:
                    if li and hasattr(li, 'find'):
                        h3_element = li.find('h3')  # type: ignore
                        if h3_element and hasattr(h3_element, 'get_text'):
                            set_includes_items.append(h3_element.get_text(strip=True))  # type: ignore
                results["set_includes"] = set_includes_items
            else:
                results["set_includes"] = []
        else:
            results["set_includes"] = None
        
        return results
        
    except Exception as e:
        print(f"Error scraping {product_name}: {e}")
        return {"name": product_name, "url": url, "type": classify_product_type(product_name, None), "error": str(e)}

def fix_benefits_formatting(text):
    """
    Fix formatting issues in benefits text by adding spaces between 
    fully capitalized words and the following lowercase words.
    """
    if not text:
        return text
    
    # Improved pattern to match fully capitalized words (including hyphens/spaces) followed by a capitalized word with lowercase
    pattern = r'([A-Z][A-Z\s-]+)([A-Z][a-z])'
    fixed_text = re.sub(pattern, r'\1 \2', text)
    return fixed_text

def main():
    """Main function to scrape all products from CSV."""
    all_products = []
    
    # Read products from CSV
    with open('products.csv', 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        products = list(reader)
    
    print(f"Found {len(products)} products to scrape")
    print("-" * 50)
    
    # Scrape each product
    for i, product in enumerate(products, 1):
        print(f"Processing {i}/{len(products)}: {product['name']}")
        
        product_data = scrape_product_details(product['url'], product['name'])
        all_products.append(product_data)
        
        # Add a small delay to be respectful to the server
        if i < len(products):  # Don't delay after the last product
            time.sleep(.5)
    
    # Save all products to JSONL format (product_catalogue.txt)
    jsonl_output_path = "product_catalogue.txt"
    with open(jsonl_output_path, "w", encoding="utf-8") as f:
        for product in all_products:
            f.write(json.dumps(product, ensure_ascii=False) + '\n')
    
    # Save all products to JSON format (all_products.json)
    json_output_path = "all_products.json"
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    
    print(f"\nScraped {len(all_products)} products")
    print(f"Results saved to: {jsonl_output_path} (JSONL format)")
    print(f"Results saved to: {json_output_path} (JSON format)")
    
    # Print summary
    successful = sum(1 for p in all_products if "error" not in p)
    failed = len(all_products) - successful
    print(f"Successful: {successful}, Failed: {failed}")

if __name__ == "__main__":
    main() 
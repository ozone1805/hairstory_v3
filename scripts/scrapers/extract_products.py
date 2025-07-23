#!/usr/bin/env python3
"""
Script to extract product URLs and names from card-product tags in HTML.
Handles saved webpage format with line numbers and formatting.
"""

import re
from bs4 import BeautifulSoup, Tag
import sys
from typing import List, Dict, Optional
import csv

def extract_actual_html(html_file_path: str) -> Optional[str]:
    """
    Extract the actual HTML content from a saved webpage format.
    
    Args:
        html_file_path (str): Path to the HTML file
        
    Returns:
        str: The actual HTML content
    """
    try:
        with open(html_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Parse the saved webpage format
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all line-content cells and extract their content
        line_contents = soup.find_all('td', class_='line-content')
        
        # Extract the text content from each line-content cell
        html_lines = []
        for line_content in line_contents:
            if isinstance(line_content, Tag):
                # Get the text content, which contains the actual HTML
                text_content = line_content.get_text()
                if text_content.strip():
                    html_lines.append(text_content)
        
        # Join all lines to reconstruct the actual HTML
        actual_html = '\n'.join(html_lines)
        
        return actual_html
        
    except Exception as e:
        print(f"Error extracting HTML: {e}")
        return None

def make_full_url(url: str) -> str:
    if url.startswith('http://') or url.startswith('https://'):
        return url
    # Ensure no double slashes
    return f"https://hairstory.com{url}" if url.startswith('/') else f"https://hairstory.com/{url}"

def extract_products_from_html(html_file_path: str) -> List[Dict[str, str]]:
    """
    Extract product URLs and names from card-product tags in HTML file.
    
    Args:
        html_file_path (str): Path to the HTML file
        
    Returns:
        list: List of dictionaries containing 'url' and 'name' for each product
    """
    try:
        # First extract the actual HTML from the saved webpage format
        actual_html = extract_actual_html(html_file_path)
        
        if not actual_html:
            print("Could not extract HTML content from file.")
            return []
        
        # Parse the actual HTML with BeautifulSoup
        soup = BeautifulSoup(actual_html, 'html.parser')
        
        # Find all card-product tags
        card_products = soup.find_all('card-product')
        
        print(f"Found {len(card_products)} card-product tags")
        
        products = []
        seen_products = set()  # To track duplicates
        
        for card_product in card_products:
            if isinstance(card_product, Tag):
                # Find the first href (product URL) within this card-product
                link = card_product.find('a', href=True)
                if link and isinstance(link, Tag):
                    url = link.get('href', '')
                    url = str(url) if url is not None else ''
                    full_url = make_full_url(url)
                    
                    # Find the h4 tag (product name) within this card-product
                    h4_tag = card_product.find('h4')
                    if h4_tag and isinstance(h4_tag, Tag):
                        name = h4_tag.get_text(strip=True)
                        
                        # Only add if we have both URL and name and haven't seen this product before
                        if full_url and name:
                            # Create a unique key for this product
                            product_key = f"{name}|{full_url}"
                            if product_key not in seen_products:
                                seen_products.add(product_key)
                                products.append({
                                    'url': full_url,
                                    'name': name
                                })
        
        return products
        
    except FileNotFoundError:
        print(f"Error: File '{html_file_path}' not found.")
        return []
    except Exception as e:
        print(f"Error processing file: {e}")
        import traceback
        traceback.print_exc()
        return []

def save_to_csv(products: List[Dict[str, str]], output_file: str = 'products.csv'):
    """
    Save the extracted products to a CSV file.
    
    Args:
        products (List[Dict[str, str]]): List of product dictionaries
        output_file (str): Output file name
    """
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['name', 'url'])
            writer.writeheader()
            for product in products:
                writer.writerow({'name': product['name'], 'url': product['url']})
        print(f"Products saved to {output_file}")
    except Exception as e:
        print(f"Error saving to CSV file: {e}")

def main():
    """Main function to run the script."""
    # Default file path
    html_file = 'shop-all.html'
    # TODO: make this grab from a live url, not a file
    
    # Check if a different file path was provided as command line argument
    if len(sys.argv) > 1:
        html_file = sys.argv[1]
    
    print(f"Extracting products from: {html_file}")
    print("-" * 50)
    
    # Extract products
    products = extract_products_from_html(html_file)
    
    if products:
        print(f"Found {len(products)} unique products:")
        print()
        
        for i, product in enumerate(products, 1):
            print(f"{i:2d}. {product['name']}")
            print(f"    URL: {product['url']}")
            print()
        
        # Save to file
        save_to_csv(products)
    else:
        print("No products found or error occurred.")

if __name__ == "__main__":
    main() 
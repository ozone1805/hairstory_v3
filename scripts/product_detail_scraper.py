import sys
import requests
from bs4 import BeautifulSoup
import json
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
        set_includes_element = soup.select_one('div[content-type="set-includes"]')
        if set_includes_element:
            return "bundle"
    
    # Everything else is a singleton
    return "singleton"

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

# Accept URL as a command-line argument, or use default
if len(sys.argv) > 1:
    url = sys.argv[1]
else:
    url = "https://hairstory.com/products/pre-wash-4-oz"

# Fetch the HTML from the URL
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
response = requests.get(url, headers=headers)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

# Use the original selectors
selectors = {
    "title": "#MainContent h1",
    "subtitle": "#MainContent h2",
    "details": "div#ProductDescription",
    "benefits": "div[content-type='benefit']",
    "how_to_use": "div[content-type='how_to_use']",
    "ingredients": "div[content-type='ingredients']"
}

# Extract text content
results = {}
for key, selector in selectors.items():
    if key == "title":
        # Special handling for title: join all spans with spaces if present
        h1 = soup.select_one("#MainContent h1")
        if h1:
            spans = h1.find_all("span")
            if spans:
                results[key] = " ".join(span.get_text(strip=True) for span in spans)
            else:
                results[key] = h1.get_text(strip=True)
        else:
            results[key] = None
    else:
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
product_name = results.get("title", "Unknown Product")
results["type"] = classify_product_type(product_name, soup)

# Extract set_includes for bundle products
if results["type"] == "bundle":
    set_includes_div = soup.select_one('div[content-type="set-includes"]')
    if set_includes_div:
        set_includes_items = []
        li_elements = set_includes_div.find_all('li')
        for li in li_elements:
            if hasattr(li, 'find'):
                h3_element = li.find('h3')  # type: ignore
                if h3_element and hasattr(h3_element, 'get_text'):
                    set_includes_items.append(h3_element.get_text(strip=True))  # type: ignore
        results["set_includes"] = set_includes_items
    else:
        results["set_includes"] = []
else:
    results["set_includes"] = None

# Print results to console only
print(json.dumps(results, indent=2))

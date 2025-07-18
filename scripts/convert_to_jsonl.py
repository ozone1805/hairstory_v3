import json

def convert_json_to_jsonl():
    """Convert all_products.json to JSONL format and save as product_catalogue.txt"""
    
    # Read the JSON file
    with open('all_products.json', 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    # Write each product as a separate line in JSONL format
    with open('product_catalogue.txt', 'w', encoding='utf-8') as f:
        for product in products:
            f.write(json.dumps(product, ensure_ascii=False) + '\n')
    
    print(f"Converted {len(products)} products to JSONL format")
    print("Saved as: product_catalogue.txt")

if __name__ == "__main__":
    convert_json_to_jsonl() 
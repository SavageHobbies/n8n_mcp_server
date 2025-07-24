#!/usr/bin/env python3
import json, sys
import requests
import os

payload = json.loads(sys.stdin.read())
upc = payload.get("upc", "")

result = {}
raw_upc_data = {}

# --- UPCitemdb.com (Trial API) ---
try:
    upcitemdb_url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={upc}" # CORRECTED URL
    upcitemdb_response = requests.get(upcitemdb_url, timeout=10)
    upcitemdb_response.raise_for_status()
    upcitemdb_data = upcitemdb_response.json()
    raw_upc_data['upcitemdb'] = upcitemdb_data

    if upcitemdb_data and upcitemdb_data.get('items'):
        item = upcitemdb_data['items'][0]
        result['title'] = item.get('title')
        result['description'] = item.get('description')
        if item.get('offers'):
            prices = [offer.get('price') for offer in item['offers'] if offer.get('price') is not None]
            if prices:
                result['lowest_price_upc'] = min(prices)
                result['highest_price_upc'] = max(prices)
        if item.get('images'):
            result['images'] = item['images']

except requests.exceptions.RequestException as e:
    sys.stderr.write(f"Error querying UPCitemdb.com: {e}\n")
except Exception as e:
    sys.stderr.write(f"Error processing UPCitemdb.com data: {e}\n")

# --- upcdatabase.org ---
UPC_DATABASE_API_KEY = os.environ.get("UPC_DATABASE_API_KEY")

if UPC_DATABASE_API_KEY:
    try:
        upcdatabase_url = f"https://api.upcdatabase.org/v1/product/{upc}"
        headers = {"Authorization": f"Bearer {UPC_DATABASE_API_KEY}"}
        upcdatabase_response = requests.get(upcdatabase_url, headers=headers, timeout=10)
        upcdatabase_response.raise_for_status()
        upcdatabase_data = upcdatabase_response.json()
        raw_upc_data['upcdatabase_org'] = upcdatabase_data

        if upcdatabase_data and upcdatabase_data.get('success'):
            product = upcdatabase_data.get('item')
            if product:
                result['title'] = result.get('title') or product.get('title')
                result['description'] = result.get('description') or product.get('description')
                result['price'] = result.get('price') or product.get('avg_price')
                if product.get('images'):
                    result['images'] = result.get('images') or product['images']

    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"Error querying upcdatabase.org: {e}\n")
    except Exception as e:
        sys.stderr.write(f"Error processing upcdatabase.org data: {e}\n")
else:
    sys.stderr.write("UPC_DATABASE_API_KEY not found in environment variables. Skipping upcdatabase.org lookup.\n")

if not result.get('title'):
    result['title'] = f"Product Title for UPC {upc} (No external data)"
if not result.get('description'):
    result['description'] = "No description available from external UPC sources."
if not result.get('price'):
    result['price'] = 0.00

if not result.get('images'):
    result['images'] = []

final_output = {
    "title": result.get('title'),
    "description": result.get('description'),
    "price": result.get('price'),
    "lowest_price": result.get('lowest_price_upc', result.get('price')),
    "highest_price": result.get('highest_price_upc', result.get('price')),
    "images": result.get('images'),
    "raw_data": raw_upc_data
}
print(json.dumps(final_output))
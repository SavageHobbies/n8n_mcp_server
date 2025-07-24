#!/usr/bin/env python3
import json, sys
import os
from sp_api.api import Catalog
from sp_api.base import Marketplaces

payload = json.loads(sys.stdin.read())
upc = payload.get("upc", "")

AMAZON_CLIENT_ID = os.environ.get("AMAZON_CLIENT_ID")
AMAZON_CLIENT_SECRET = os.environ.get("AMAZON_CLIENT_SECRET")
AMAZON_REFRESH_TOKEN = os.environ.get("AMAZON_REFRESH_TOKEN")
AMAZON_REGION = os.environ.get("AMAZON_REGION", "us-east-1") 

MARKETPLACE_MAP = {
    "us-east-1": Marketplaces.US,
    "eu-west-1": Marketplaces.DE, 
}
marketplace = MARKETPLACE_MAP.get(AMAZON_REGION, Marketplaces.US)

result = {
    "title": f"Amazon listing {upc} (Not Found)",
    "description": "Amazon data not found.",
    "price": 0.00,
    "images": [],
    "raw_data": {}
}

if not all([AMAZON_CLIENT_ID, AMAZON_CLIENT_SECRET, AMAZON_REFRESH_TOKEN]):
    sys.stderr.write("Amazon SP-API credentials missing. Skipping Amazon lookup.\n")
elif not Catalog:
    sys.stderr.write("python-amazon-sp-api Catalog client not available. Skipping Amazon lookup.\n")
else:
    try:
        credentials = {
            'lwa_app_id': AMAZON_CLIENT_ID,
            'lwa_client_secret': AMAZON_CLIENT_SECRET,
            'refresh_token': AMAZON_REFRESH_TOKEN
        }
        catalog_client = Catalog(credentials=credentials, marketplace=marketplace)

        response = catalog_client.search_catalog_items(
            item_locale='en_US', 
            identifiers=[upc],
            identifiers_type='UPC', 
            marketplace_ids=[marketplace.marketplace_id]
        )

        result["raw_data"] = response.payload

        if response.payload and response.payload.get('items'):
            item = response.payload['items'][0]
            summaries = item.get('summaries', [])
            images = item.get('images', [])
            offers = item.get('offers', [])

            if summaries:
                summary = summaries[0]
                result['title'] = summary.get('item_name')
                result['description'] = summary.get('brand') 

            if images:
                result['images'] = [img.get('link') for img in images if img.get('link')]

            if offers:
                min_price = float('inf')
                for offer in offers:
                    if offer.get('offers'):
                        for offer_detail in offer['offers']:
                            price_details = offer_detail.get('price')
                            if price_details and price_details.get('amount') is not None:
                                current_price = price_details['amount']
                                if current_price < min_price:
                                    min_price = current_price
                if min_price != float('inf'):
                    result['price'] = min_price
                else:
                    result['price'] = 0.00 
            else:
                result['price'] = 0.00 

    except Exception as e:
        sys.stderr.write(f"Amazon SP-API Error for UPC {upc}: {e}\n")
        result = {
            "title": f"Amazon listing {upc} (Error)",
            "description": f"Amazon API call failed: {e}",
            "price": 0.00,
            "images": [],
            "raw_data": {}
        }

print(json.dumps(result))
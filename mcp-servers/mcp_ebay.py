#!/usr/bin/env python3
import json, sys
import os
from ebaysdk.finding import Connection as FindingAPI
from ebaysdk.exception import ConnectionError as EbayConnectionError

payload = json.loads(sys.stdin.read())
upc = payload.get("upc", "")

EBAY_APP_ID = os.environ.get("EBAY_APP_ID")
EBAY_ENVIRONMENT = os.environ.get("EBAY_ENVIRONMENT", "production") 

result = {
    "title": f"eBay listing {upc} (Not Found)",
    "description": "eBay data not found.",
    "price": 0.00,
    "images": [],
    "raw_data": {}
}

if not EBAY_APP_ID:
    sys.stderr.write("eBay APP_ID missing. Skipping eBay lookup.\n")
elif not FindingAPI:
    sys.stderr.write("ebaysdk Finding API client not available. Skipping eBay lookup.\n")
else:
    try:
        api = FindingAPI(
            appid=EBAY_APP_ID,
            config_file=None, 
            domain='svcs.ebay.com' if EBAY_ENVIRONMENT == 'production' else 'svcs.sandbox.ebay.com'
        )

        response = api.execute('findItemsByProduct', {
            'productId': {
                '_value': upc,
                'type': 'UPC' 
            },
            'outputSelector': ['PictureURLSuperSize', 'GalleryInfo', 'PictureURL']
        })

        result["raw_data"] = response.dict()

        if response.dict() and response.dict().get('searchResult') and response.dict()['searchResult'].get('item'):
            item = response.dict()['searchResult']['item'][0]

            result['title'] = item.get('title')
            result['description'] = item.get('subtitle') 

            selling_status = item.get('sellingStatus', {})
            current_price = selling_status.get('currentPrice', {}).get('value')
            if current_price is not None:
                result['price'] = float(current_price)
            else:
                result['price'] = 0.00 

            image_urls = []
            if item.get('galleryURL'):
                image_urls.append(item['galleryURL'])
            if item.get('pictureURLSuperSize'):
                image_urls.append(item['pictureURLSuperSize'])
            elif item.get('pictureURLLarge'):
                image_urls.append(item['pictureURLLarge'])

            result['images'] = image_urls

    except EbayConnectionError as e:
        sys.stderr.write(f"eBay API Connection Error for UPC {upc}: {e.response.dict() if e.response else e}\n")
        result = {
            "title": f"eBay listing {upc} (Error)",
            "description": f"eBay API call failed: {e}",
            "price": 0.00,
            "images": [],
            "raw_data": {}
        }
    except Exception as e:
        sys.stderr.write(f"eBay API Error for UPC {upc}: {e}\n")
        result = {
            "title": f"eBay listing {upc} (Error)",
            "description": f"eBay API call failed: {e}",
            "price": 0.00,
            "images": [],
            "raw_data": {}
        }

print(json.dumps(result))
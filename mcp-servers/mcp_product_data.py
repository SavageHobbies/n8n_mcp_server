import json
import sys
import os
import logging
import requests
import base64 # Added for base64 decoding input from n8n
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MCPRequest:
    jsonrpc: str
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None

@dataclass
class MCPResponse:
    jsonrpc: str
    id: Optional[str]
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

class UPCDataSource:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url

    def get_product_data(self, upc: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def _standardize_data(self, data: Dict[str, Any], source: str) -> Dict[str, Any]:
        # Default standardization, override in subclasses if needed
        standardized_output = {
            "product_name": data.get("title", data.get("productname", "")),
            "description": data.get("description", ""),
            "brand": data.get("brand", ""),
            "category": data.get("category", ""),
            "images_urls": data.get("images", data.get("image_urls", [])),
            "ean": data.get("ean", ""),
            "mpn": data.get("mpn", ""),
            "model": data.get("model", ""),
            "price": data.get("price", None),
            "currency": data.get("currency", "USD"),
            "features_list": data.get("features", []),
            "manufacturer": data.get("manufacturer", ""),
            "dimensions": data.get("dimensions", ""),
            "weight": data.get("weight", ""),
            "upc": data.get("upc", upc), # This `upc` should be the parameter passed from get_product_data
            "success": True,
            "source_used": source
        }
        logger.info(f"DEBUG: Standardized data from {source}: {standardized_output}")
        return standardized_output

class UPCDatabaseOrg(UPCDataSource):
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.upcdatabase.org/product/")

    def get_product_data(self, upc: str) -> Optional[Dict[str, Any]]:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.base_url}{upc}", headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("success") and data.get("item_name"):
                logger.info(f"Data found on upcdatabase.org for UPC: {upc}")
                # Map upcdatabase.org specific fields to a common format
                standardized_data = {
                    "title": data.get("item_name"),
                    "description": data.get("description"),
                    "brand": data.get("brand"),
                    "category": data.get("category"),
                    "image_urls": [data.get("image")] if data.get("image") else [],
                    "ean": data.get("ean"),
                    "mpn": data.get("mpn"),
                    "model": data.get("model"),
                    "price": data.get("price"),
                    "currency": data.get("currency"),
                    "features": data.get("features", []),
                    "manufacturer": data.get("manufacturer"),
                    "dimensions": data.get("dimensions", ""),
                    "weight": data.get("weight"),
                    "upc": data.get("upc")
                }
                return self._standardize_data(standardized_data, "upcdatabase.org")
            else:
                logger.warning(f"No data or unsuccessful response from upcdatabase.org for UPC: {upc}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching from upcdatabase.org for UPC {upc}: {e}")
            return None

class UPCItemDB(UPCDataSource):
    def __init__(self, api_key: str = None):
        super().__init__(api_key, "https://api.upcitemdb.com/prod/trial/lookup")

    def get_product_data(self, upc: str) -> Optional[Dict[str, Any]]:
        try:
            params = {"upc": upc}
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("items"):
                item = data["items"][0]
                logger.info(f"DEBUG: UPCItemDB raw item data: {item}") # DEBUG
                logger.info(f"Data found on upcitemdb.com for UPC: {upc}")
                standardized_data = {
                    "title": item.get("title"),
                    "description": item.get("description"),
                    "brand": item.get("brand"),
                    "category": item.get("category"),
                    "image_urls": item.get("images", []),
                    "ean": item.get("ean"),
                    "mpn": item.get("mpn"),
                    "model": item.get("model"),
                    "price": item.get("lowest_recorded_price"),
                    "currency": item.get("currency"),
                    "features": item.get("features", []),
                    "manufacturer": item.get("manufacturer"),
                    "dimensions": item.get("dimensions"),
                    "weight": item.get("weight"),
                    "upc": item.get("upc")
                }
                standardized_result = self._standardize_data(standardized_data, "upcitemdb.com") # Capture return
                logger.info(f"DEBUG: UPCItemDB standardized result: {standardized_result}") # DEBUG
                return standardized_result
            else:
                logger.warning(f"No data found on upcitemdb.com for UPC: {upc}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching from upcitemdb.com for UPC {upc}: {e}")
            return None

class ProductDataMCPServer:
    # HARDCODED API KEY FOR TESTING: This bypasses environment variable issues for now.
    def __init__(self):
        self.upcdatabase_api_key = "F09E8815249B0EF29029CD078A3D018C"
        self.upcitemdb_api_key = os.getenv("UPC_ITEMDB_API_KEY") # Continue to use env for this one

        self.upc_data_sources = []
        if self.upcdatabase_api_key:
            self.upc_data_sources.append(UPCDatabaseOrg(self.upcdatabase_api_key))
        else:
            logger.warning("UPC_DATABASE_API_KEY is not set (hardcoded or env var missing). Skipping upcdatabase.org.")

        self.upc_data_sources.append(UPCItemDB(self.upcitemdb_api_key))

        if not self.upc_data_sources:
            logger.error("No UPC data sources configured. Please set at least one API key.")

    def handle_request(self, request_data: str) -> str:
        try:
            # request_data is now expected to be the actual JSON-RPC string
            # (since main() already extracted it from n8n's full event object)
            request_json = json.loads(request_data)
            logger.info(f"DEBUG: handle_request received JSON-RPC: {request_json}") # Debug to confirm it

            # This 'request_json' variable IS already the correct JSON-RPC body.
            # No further extraction from 'original.body' is needed here.
            request = MCPRequest(
                jsonrpc=request_json.get("jsonrpc", "2.0"),
                method=request_json.get("method"),
                params=request_json.get("params", {}),
                id=request_json.get("id")
            )

            result = {}
            if request.method == "getProductDataByUPC":
                # RENAMED PARAMETER TO AVOID POTENTIAL SCOPE ISSUES
                upc_from_request = request.params.get("upc")
                if upc_from_request:
                    result = self.getProductDataByUPC(upc_from_request) # Pass the renamed parameter
                else:
                    result = {"error": "Missing 'upc' parameter", "code": 400}
            elif request.method == "initialize":
                result = self.initialize()
            elif request.method == "list_tools":
                result = self.list_tools()
            else:
                result = {"error": f"Unknown method: {request.method}", "code": 404}

            if "error" in result:
                response = MCPResponse(
                    jsonrpc="2.0",
                    id=request.id,
                    error={"code": result.get("code", 500), "message": result["error"], "data": result.get("details")}
                )
            else:
                response = MCPResponse(
                    jsonrpc="2.0",
                    id=request.id,
                    result=result
                )

            return json.dumps({
                "jsonrpc": response.jsonrpc,
                "id": response.id,
                "result": response.result,
                "error": response.error
            })

        except json.JSONDecodeError as e:
            error_response = MCPResponse(
                jsonrpc="2.0",
                id=None,
                error={"code": -32700, "message": "Parse error", "data": str(e)}
            )
            return json.dumps({
                "jsonrpc": error_response.jsonrpc,
                "id": error_response.id,
                "error": error_response.error
            })
        except Exception as e:
            request_id = request.id if 'request' in locals() and hasattr(request, 'id') else None
            error_response = MCPResponse(
                jsonrpc="2.0",
                id=request_id,
                error={"code": -32603, "message": "Internal error", "data": str(e)}
            )
            return json.dumps({
                "jsonrpc": error_response.jsonrpc,
                "id": error_response.id,
                "error": error_response.error
            })

    def initialize(self) -> Dict[str, Any]:
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "mcp-product-data",
                "version": "1.0.0"
            }
        }

    def list_tools(self) -> Dict[str, Any]:
        return {
            "tools": [
                {
                    "name": "getProductDataByUPC",
                    "description": "Takes a UPC string and returns comprehensive product data.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "upc": {"type": "string", "description": "The UPC string to look up."}
                        },
                        "required": ["upc"]
                    }
                }
            ]
        }

    def getProductDataByUPC(self, input_upc: str) -> Dict[str, Any]: # RENAMED PARAMETER FOR CLARITY
        logger.info(f"DEBUG: getProductDataByUPC called for UPC: {input_upc}")
        for source in self.upc_data_sources:
            logger.info(f"DEBUG: Checking source: {source.__class__.__name__}")
            product_data = source.get_product_data(input_upc) # Use input_upc here
            logger.info(f"DEBUG: Result from {source.__class__.__name__}: {product_data} (type: {type(product_data)})")
            if product_data:
                logger.info(f"DEBUG: Found valid product_data from {source.__class__.__name__}. Attempting to return.")
                return product_data
            else:
                logger.info(f"DEBUG: No valid data received from {source.__class__.__name__}.")

        logger.error(f"DEBUG: getProductDataByUPC loop finished. No source returned valid data.")
        try:
            # Explicitly check if input_upc is defined here before using it in f-string
            final_message_upc = input_upc # Assign to a new variable just to be absolutely sure of scope
            logger.error(f"DEBUG: Final return - input_upc is: {final_message_upc}")
        except NameError:
            logger.error(f"DEBUG: NameError: input_upc is not defined in final return block!")
            final_message_upc = "UNKNOWN_UPC_ERROR" # Fallback if NameError occurs here

        return {"success": False, "message": f"No product data found for UPC: {final_message_upc} from any configured source.", "code": 404}


def main():
    # API KEY IS HARDCODED IN ProductDataMCPServer.__init__ for now.
    server = ProductDataMCPServer()
    logger.info("mcp-product-data started")
    try:
        # Read JSON input from stdin (this is separate from the API key argument)
        for line in sys.stdin:
            line = line.strip()
            logger.info(f"DEBUG: Raw JSON input from n8n: {line}") # KEEP THIS DEBUG LINE

            if line:
                try:
                    n8n_item_data = json.loads(line)
                    actual_json_rpc_request = n8n_item_data.get("body", {}) 

                    if not actual_json_rpc_request:
                        logger.error("Error: Could not find actual JSON-RPC request nested in n8n input.")
                        print(json.dumps({"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid n8n input structure: Missing 'original.body'"}}))
                        sys.stdout.flush()
                        continue # Skip to next line or exit

                    # Now pass the correctly extracted JSON-RPC request (as a string) to handle_request
                    response = server.handle_request(json.dumps(actual_json_rpc_request))
                    print(response)
                    sys.stdout.flush()

                except json.JSONDecodeError as e:
                    logger.error(f"JSON Decode Error parsing n8n item: {e}. Input was: {line[:500]}...")
                    print(json.dumps({"jsonrpc": "2.0", "error": {"code": -32700, "message": f"Parse error: {str(e)}"}}))
                    sys.stdout.flush()
                except Exception as e:
                    logger.exception("An unexpected error occurred during processing:")
                    print(json.dumps({"jsonrpc": "2.0", "error": {"code": -32000, "message": f"Server error: {str(e)}"}}))
                    sys.stdout.flush()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error outside main loop: {e}")

if __name__ == "__main__":
    main()

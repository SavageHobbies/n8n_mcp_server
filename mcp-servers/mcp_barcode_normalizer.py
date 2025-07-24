#!/usr/bin/env python3
"""
Normalize barcode and infer type.
stdin:  {"barcode": "...", "qty": 1}
stdout: {"barcode": "012345678905", "type": "UPC", "qty": 1}
"""
import json, sys, re

def main():
    try:
        data = json.load(sys.stdin)
        raw = str(data.get("barcode", "")).strip()
        qty = int(data.get("qty", 1))
        clean = re.sub(r"[^0-9A-Za-z]", "", raw).upper()

        if not clean:
            raise ValueError("Empty barcode")

        barcode_type = (
            "UPC"   if len(clean) == 12 else
            "EAN"   if len(clean) == 13 else
            "ASIN"  if clean.startswith("B0") and len(clean) == 10 else
            "ISBN"  if (len(clean) == 10 and clean[:9].isdigit()) or (len(clean) == 13 and clean.isdigit()) else
            "GTIN"  if len(clean) in [14] else
            "UNKNOWN"
        )

        result = {"barcode": clean, "type": barcode_type, "qty": qty}
        print(json.dumps(result))
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
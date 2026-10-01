import urllib.request
import json

def test_api():
    print("--- 1. Testing Warranty API ---")
    req = urllib.request.Request(
        "http://127.0.0.1:5000/api/warranty/check",
        data=json.dumps({"serial_number": "SN1001"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        print("Status:", res.get("status"), "| Product:", res.get("product_name"), "| Expire:", res.get("expiry_date"))

    print("\n--- 2. Testing Chat RAG API ---")
    req2 = urllib.request.Request(
        "http://127.0.0.1:5000/api/chat",
        data=json.dumps({"message": "What is the battery capacity of Laptop X1?"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req2) as resp:
        res2 = json.loads(resp.read().decode())
        print("Answer:", res2.get("answer"))
        print("Sources:", res2.get("sources"))

if __name__ == "__main__":
    test_api()

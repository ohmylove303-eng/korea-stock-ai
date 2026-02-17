import requests
import json
import os

url = "http://127.0.0.1:5001/api/kr/analyze-stock"
payload = {"ticker": "042660"}
headers = {"Content-Type": "application/json"}

try:
    print(f"Sending request to {url}...")
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(response.text[:2000]) # 처음 2000자만 출력
except Exception as e:
    print(f"Error: {e}")

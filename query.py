import requests
import json

url = "http://localhost:8000/who-said"
headers = {"Content-Type": "application/json"}
data = {"quote": "guddi sikhran di jatt ni?"}

try:
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
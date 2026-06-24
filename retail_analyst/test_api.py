import requests
import time

url = "http://localhost:8001/api/query"
payload = {
    "question": "What is the total net sales by category for 2025?",
    "conversation_history": []
}

print(f"Sending request to {url}...")
start_time = time.time()
try:
    response = requests.post(url, json=payload, timeout=120)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except requests.exceptions.Timeout:
    print("Request timed out after 30 seconds.")
except Exception as e:
    print(f"Request failed: {e}")
finally:
    print(f"Elapsed Time: {time.time() - start_time:.2f} seconds")

import os
import httpx
from dotenv import load_dotenv
load_dotenv('.env')
url = f'https://generativelanguage.googleapis.com/v1beta/models/{os.environ.get("LLM_MODEL")}:generateContent'
payload = {'contents': [{'role': 'user', 'parts': [{'text': 'hello'}]}]}
response = httpx.post(url, json=payload, params={'key': os.environ.get('LLM_API_KEY')}, headers={'Content-Type': 'application/json'}, timeout=60)
print(response.status_code)
print(response.text)

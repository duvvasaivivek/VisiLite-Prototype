import os
os.environ["VISILITE_SKIP_BROWSER"] = "1"
os.environ["VISILITE_SKIP_TEST_SITES"] = "1"
os.environ["VAULT_PASSWORD"] = "test"

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

response = client.post("/api/plan", json={
    "task": "register",
    "context": {
        "url": "http://localhost:3000",
        "title": "test",
        "elements": [],
        "elementCount": 0
    }
})
print("STATUS:", response.status_code)
print("RESPONSE:", response.text)

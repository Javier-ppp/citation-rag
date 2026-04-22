from fastapi.testclient import TestClient
from backend.main import app
import json

client = TestClient(app)

with open('backend/data/paper_registry.json', 'r') as f:
    registry = json.load(f)
main_pid = [pid for pid, m in registry.items() if m.get('role') == 'main'][0]

response = client.post(
    "/api/cite-check",
    json={"citation_marker": "[5]", "context": "sification using sparse transformers", "pdf_id": main_pid}
)
print("Status Code:", response.status_code)
print("Response:", response.text)
if response.status_code == 500:
    print("Oh no!")

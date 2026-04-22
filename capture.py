import requests

try:
    with open('backend/data/paper_registry.json', 'r') as f:
        import json
        registry = json.load(f)
    main_pid = [pid for pid, m in registry.items() if m.get('role') == 'main'][0]
    
    r = requests.post("http://localhost:8000/api/cite-check", json={
        "citation_marker": "[5]",
        "context": "sification using sparse transformers",
        "pdf_id": main_pid
    })
    print(r.status_code)
    print(r.text)
except Exception as e:
    print(e)

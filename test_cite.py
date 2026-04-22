import asyncio
from backend.services.rag_pipeline import backward_cite_check
import logging

logging.basicConfig(level=logging.ERROR)

async def main():
    try:
        # We need a valid pdf_id. Let's find one.
        import json
        with open('backend/data/paper_registry.json', 'r') as f:
            registry = json.load(f)
        main_pids = [pid for pid, m in registry.items() if m.get('role') == 'main']
        if not main_pids:
            print("No main paper found!")
            return
        main_pid = main_pids[0]
        print(f"Using main pdf: {main_pid}")
        
        result = await backward_cite_check("[1,5]", "efficient segmentation models like SAM 2", main_pid)
        print("SUCCESS:")
        
        # Validate Pydantic Model
        from backend.models import CiteCheckResponse
        resp = CiteCheckResponse(**result)
        print("Pydantic validation passed.")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

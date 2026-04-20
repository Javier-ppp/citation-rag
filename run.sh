#!/bin/bash

# Ensure virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]]; then
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        echo "Error: .venv not found. Please run environment setup first."
        exit 1
    fi
fi

# Run the backend as a module to avoid ModuleNotFoundError
echo "Starting Citation RAG API on http://localhost:8000 ..."
python3 -m backend.main

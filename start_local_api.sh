#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python -m uvicorn api.index:app --port 8000 --log-level warning

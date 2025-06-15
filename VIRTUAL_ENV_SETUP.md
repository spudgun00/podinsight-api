# Virtual Environment Setup

## Current Setup
- Virtual environment directory: `venv/` (NOT `.venv`)
- Created with: `python3 -m venv venv`
- Python version: 3.9+ (compatible with Vercel's Python 3.12)

## Activation
```bash
source venv/bin/activate
```

## Deactivation
```bash
deactivate
```

## Installing Dependencies
Always activate the virtual environment first:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Running the API Locally
```bash
source venv/bin/activate
uvicorn api.topic_velocity:app --reload --port 8000
```

## Important Notes
- The virtual environment is already created and exists in the `venv/` directory
- Always activate the virtual environment before installing packages or running the API
- The `.gitignore` file already excludes the `venv/` directory from version control
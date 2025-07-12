# MongoDB Authentication Fix

## The Problem
There's a recurring issue where MongoDB authentication fails because the shell environment has an incorrect MONGODB_URI that overrides the .env file.

- Shell environment has: `coq6u2huF1pVEtoae` (wrong - extra 'e' at end)
- .env file has: `coq6u2huF1pVEtoa` (correct)

## The Solution

### 1. Immediate Fix (for current session)
```bash
unset MONGODB_URI
```

### 2. Permanent Fix (implemented)

All Python files now import `lib.env_loader` which:
- Forces .env values to override shell environment
- Detects and fixes the incorrect password
- Ensures consistent environment across all modules

### 3. Using the API

Always start the API using:
```bash
./start_api.sh
```

Or if running Python directly:
```bash
unset MONGODB_URI && python your_script.py
```

### 4. For Vercel Deployment

The environment variables in Vercel dashboard are correct. This issue only affects local development.

## Files Updated
- Created `lib/env_loader.py` - Environment loading utility
- Updated `api/improved_hybrid_search.py` - Added env_loader import
- Updated `api/search_lightweight_768d.py` - Added env_loader import
- Created `setup_env.sh` - Shell script to set environment
- Created `start_api.sh` - API startup script

## Why This Keeps Happening

The shell environment variable persists across sessions and overrides .env files by default. The python-dotenv library respects existing environment variables unless explicitly told to override them with `override=True`.

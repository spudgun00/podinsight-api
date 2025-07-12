"""
Environment loader that ensures .env file takes precedence over shell environment.
This prevents the recurring MongoDB authentication issues.
"""

import os
from pathlib import Path

def load_env_safely():
    """
    Load environment variables from .env file, ensuring they override
    any existing shell environment variables.
    """
    # In Vercel/production, env vars are already loaded
    # Check for VERCEL environment variable
    if os.getenv("VERCEL") or os.getenv("VERCEL_ENV"):
        # Running in Vercel, no need to load .env file
        return True

    # Only try to load .env file in local development
    try:
        from dotenv import load_dotenv

        # Find the .env file
        env_path = Path(__file__).parent.parent / '.env'

        if not env_path.exists():
            # In production or if .env doesn't exist, just continue
            print(f"Note: .env file not found at {env_path}, using system environment variables")
            return True

        # IMPORTANT: override=True ensures .env values take precedence over shell
        load_dotenv(env_path, override=True)

        # Verify MongoDB URI is loaded correctly
        mongodb_uri = os.getenv("MONGODB_URI")
        if mongodb_uri and "coq6u2huF1pVEtoae" in mongodb_uri:
            # This is the incorrect password with extra 'e'
            print("⚠️  WARNING: MongoDB URI has incorrect password. Reloading from .env...")

            # Force reload by unsetting and reloading
            if "MONGODB_URI" in os.environ:
                del os.environ["MONGODB_URI"]

            # Reload with override
            load_dotenv(env_path, override=True)
    except ImportError:
        # python-dotenv not available (shouldn't happen now)
        print("Note: python-dotenv not available, using system environment variables")

    return True

# Auto-load on import
load_env_safely()

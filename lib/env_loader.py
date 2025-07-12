"""
Environment loader that ensures .env file takes precedence over shell environment.
This prevents the recurring MongoDB authentication issues.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

def load_env_safely():
    """
    Load environment variables from .env file, ensuring they override
    any existing shell environment variables.
    """
    # Find the .env file
    env_path = Path(__file__).parent.parent / '.env'

    if not env_path.exists():
        raise FileNotFoundError(f".env file not found at {env_path}")

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

    return True

# Auto-load on import
load_env_safely()

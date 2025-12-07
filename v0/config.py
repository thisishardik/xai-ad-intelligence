"""
Centralized configuration for the Ad Intelligence Pipeline.
All environment variables and settings are managed here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env (preferred) and then v0/.env
_here = Path(__file__).resolve().parent
_root_env = _here.parent / ".env"
_local_env = _here / ".env"
load_dotenv(_root_env, override=False)
load_dotenv(_local_env, override=False)

# API Keys
XAI_API_KEY = os.getenv("XAI_API_KEY")
X_CLIENT_ID = os.getenv("X_CLIENT_ID")

# Auth Server Configuration
AUTH_SERVER_HOST = os.getenv("AUTH_SERVER_HOST", "127.0.0.1")
AUTH_SERVER_PORT = int(os.getenv("AUTH_SERVER_PORT", "8000"))
AUTH_SERVER_URL = f"http://{AUTH_SERVER_HOST}:{AUTH_SERVER_PORT}"
REDIRECT_URI = f"{AUTH_SERVER_URL}/callback"

# OAuth Scopes
OAUTH_SCOPES = "tweet.read users.read offline.access bookmark.read like.read"

# Model Configuration
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "grok-4-1-fast-non-reasoning")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "grok-2-image")  # For generating images
VISION_MODEL = os.getenv("VISION_MODEL", "grok-2-vision-1212")  # For analyzing/understanding images

# CTR Prediction Configuration
CTR_ENSEMBLE_RUNS = int(os.getenv("CTR_ENSEMBLE_RUNS", "10"))

# Default Ads (can be overridden)
DEFAULT_ADS = [
    "Experience endless entertainment with 6 months of premium streaming for free.",
    "Save more on groceries every week with the FreshMart Rewards Card.",
    "Travel to your dream destinations—flight deals starting at just $199 round trip!",
    "Stay powered all day with our latest PowerMax portable charger.",
    "Unlock your coding potential with 50% off our leading online programming courses.",
    "Feel the comfort of all-season shoes, now with enhanced arch support.",
    "Protect your home 24/7—introducing the SmartSecure security system.",
    "Get crystal-clear video calls with the new VisionHD webcam.",
    "Level up your workspace with the ergonomic Elevate Office Chair—on sale now!"
]


def validate_config():
    """Validate that all required configuration is present."""
    missing = []
    
    if not XAI_API_KEY:
        missing.append("XAI_API_KEY")
    if not X_CLIENT_ID:
        missing.append("X_CLIENT_ID")
    
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Please create a .env file in the v0 directory with these values."
        )
    
    return True

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from supabase import Client, create_client


class SupabaseConfigError(RuntimeError):
    """Raised when Supabase configuration is missing."""


def _load_env_once() -> None:
    """Load environment variables from likely .env locations (idempotent)."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / ".env",              # v0/.env
        here.parent / ".env",       # repo root .env
    ]
    for path in candidates:
        load_dotenv(path, override=False)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Create (and cache) a Supabase client for server-side use.
    Expects env vars:
    - SUPABASE_URL
    - SUPABASE_SERVICE_ROLE_KEY (preferred) or SUPABASE_ANON_KEY
    """
    _load_env_once()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise SupabaseConfigError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) are required")
    return create_client(url, key)


def fetch_ads(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch recent ads from ad_campaigns with fields needed for remixing.
    """
    supabase = get_supabase_client()
    response = (
        supabase.table("ad_campaigns")
        .select(
            "id,title,description,company,tagline,image_url,company_persona,strictly_against,categories,created_at"
        )
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []


if __name__ == "__main__":
    # Simple smoke test to verify env + Supabase fetch
    try:
        ads = fetch_ads(limit=5)
        print(f"Fetched {len(ads)} ads from Supabase.")
        for i, ad in enumerate(ads, 1):
            title = ad.get("title") or ad.get("description") or "(no title)"
            print(f"{i}. {title}")
    except Exception as e:
        print(f"Supabase fetch failed: {e}")


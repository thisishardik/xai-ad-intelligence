import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client


class SupabaseConfigError(RuntimeError):
    """Raised when Supabase configuration is missing."""


def _load_env_once() -> None:
    # Load root .env (preferred) then local .env without overriding set vars
    here = Path(__file__).resolve().parent
    root_env = here.parent.parent / ".env"  # repo root
    local_env = here / ".env"
    load_dotenv(root_env, override=False)
    load_dotenv(local_env, override=False)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Create (and cache) a Supabase client for server-side use.

    Expects the following env vars:
    - SUPABASE_URL
    - SUPABASE_SERVICE_ROLE_KEY (preferred for server-side reads under RLS)
    """
    _load_env_once()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise SupabaseConfigError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) are required")
    return create_client(url, key)


def fetch_ads(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch recent ads with the fields required for scoring/remixing.
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


def fetch_persona(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a stored persona for a given user.
    Expects a `personas` table with at least: user_id, persona, strictly_against, categories (optional).
    """
    supabase = get_supabase_client()
    response = (
        supabase.table("personas")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if response.data:
        return response.data[0]
    return None



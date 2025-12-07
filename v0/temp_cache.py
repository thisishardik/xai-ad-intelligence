"""
Lightweight temp cache for ad queues consumed by the Chrome extension.

Responsibilities
- Persist per-user ad queues to JSON files under temp_ad_cache/
- Track which ads have already been shown (by ad_key) to avoid repeats
- Provide helpers to pop/append ads atomically
- Share common helpers for ad key computation and best-variant formatting
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from threading import RLock
from typing import Dict, List, Tuple, Optional, Iterable, Any

BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "temp_ad_cache"
CACHE_DIR.mkdir(exist_ok=True)

_lock = RLock()


def _cache_file(user_id: str) -> Path:
    safe_user = user_id.replace("/", "_")
    return CACHE_DIR / f"{safe_user}_queue.json"


def compute_ad_key(ad: Dict[str, Any]) -> str:
    """Create a stable identifier for an original ad."""
    if not ad:
        return "unknown_ad"
    if ad.get("id"):
        return f"id:{ad.get('id')}"

    text_parts = [
        ad.get("title") or "",
        ad.get("description") or "",
        ad.get("tagline") or "",
        ad.get("text") or "",
    ]
    text = " — ".join([t for t in text_parts if t])
    image_url = ad.get("image_url") or ad.get("image") or ""
    digest = hashlib.sha256(f"{text}||{image_url}".encode("utf-8")).hexdigest()
    return f"hash:{digest}"


def format_best_variant_for_cache(best_variant_result: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Normalize best-variant result into the shape expected by the injection client.
    """
    best_variant = best_variant_result["best_variant"]
    content = getattr(best_variant, "content", "") or best_variant.get("content", "")

    image_uri = (
        getattr(best_variant, "image_uri", None)
        or getattr(best_variant, "enhanced_image_uri", None)
        or getattr(best_variant, "original_image_uri", None)
        or best_variant.get("image_uri")
    )

    lines = content.split("\n")
    title = lines[0].strip() if lines else "Sponsored Ad"
    description = lines[1].strip() if len(lines) > 1 else ""

    return {
        "id": f"{user_id}_ad_{best_variant_result.get('ad_index', 0)}",
        "title": title,
        "description": description,
        "full_content": content,
        "image_uri": image_uri,
        "brand": "AI Personalized",
        "avatar": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png",
        "ctr_score": best_variant_result.get("ctr_score", 0),
        "confidence": best_variant_result.get("confidence", 0),
        "ad_index": best_variant_result.get("ad_index", 0),
        "original_ad": best_variant_result.get("original_ad"),
        "ad_key": best_variant_result.get("ad_key"),
        "total_variants": len(best_variant_result.get("all_variants", [])),
    }


def _default_state(user_id: str, username: Optional[str] = None) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "username": username or user_id,
        "queue": [],
        "served_keys": [],
    }


def load_queue_state(user_id: str) -> Tuple[Dict[str, Any], Path]:
    """Load queue state for user, creating a default if missing."""
    path = _cache_file(user_id)
    with _lock:
        if path.exists():
            try:
                data = json.loads(path.read_text())
                data.setdefault("queue", [])
                data.setdefault("served_keys", [])
                data.setdefault("user_id", user_id)
                data.setdefault("username", user_id)
                return data, path
            except Exception:
                # Corrupt file fallback
                pass

        data = _default_state(user_id)
        path.write_text(json.dumps(data, indent=2))
        return data, path


def save_queue_state(user_id: str, data: Dict[str, Any]) -> Path:
    """Persist queue state for user."""
    path = _cache_file(user_id)
    with _lock:
        path.write_text(json.dumps(data, indent=2))
    return path


def replace_queue(user_id: str, username: str, queue: List[Dict[str, Any]], served_keys: Iterable[str] = ()) -> Path:
    """Replace queue entirely, preserving served history."""
    data = _default_state(user_id, username)
    data["queue"] = queue
    data["served_keys"] = list(dict.fromkeys(served_keys or []))
    return save_queue_state(user_id, data)


def append_ads_to_queue(
    user_id: str,
    ads: List[Dict[str, Any]],
    username: Optional[str] = None,
) -> int:
    """Append ads to queue, skipping duplicates and previously served keys."""
    state, _ = load_queue_state(user_id)
    if username:
        state["username"] = username

    served = set(state.get("served_keys", []))
    existing = {ad.get("ad_key") for ad in state.get("queue", []) if ad.get("ad_key")}

    added = 0
    for ad in ads:
        ad_key = ad.get("ad_key")
        if ad_key and (ad_key in served or ad_key in existing):
            continue
        state["queue"].append(ad)
        if ad_key:
            existing.add(ad_key)
        added += 1

    save_queue_state(user_id, state)
    return added


def pop_next_ad(user_id: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Pop the next ad from queue and record it as served."""
    state, _ = load_queue_state(user_id)
    queue = state.get("queue", [])
    if not queue:
        return None, state

    ad = queue.pop(0)
    ad_key = ad.get("ad_key")
    if ad_key:
        state.setdefault("served_keys", [])
        state["served_keys"].append(ad_key)

    state["queue"] = queue
    save_queue_state(user_id, state)
    return ad, state


def queue_size(user_id: str) -> int:
    state, _ = load_queue_state(user_id)
    return len(state.get("queue", []))


def cache_file_path(user_id: str) -> Path:
    return _cache_file(user_id)

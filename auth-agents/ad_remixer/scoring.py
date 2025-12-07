from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


def _to_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        parts = re.split(r"[;,]", value)
        return [p.strip() for p in parts if p.strip()]
    return []


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    return re.findall(r"[a-zA-Z0-9']+", text.lower())


def _overlap_score(a: List[str], b: List[str]) -> float:
    if not a or not b:
        return 0.0
    set_a, set_b = set(a), set(b)
    overlap = len(set_a & set_b)
    return overlap / max(len(set_a), 1)


def _penalty_for_banned(banned: List[str], text: str) -> float:
    if not banned:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for b in banned if b.lower() in text_lower)
    return min(hits * 0.25, 1.0)  # up to full penalty


def score_ad(ad: Dict[str, Any], persona: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a single ad against a persona.
    Returns per-factor scores (0-100) and a total.
    """
    persona_text = str(persona.get("persona") or persona.get("company_persona") or "")
    persona_tokens = _tokenize(persona_text)
    persona_categories = _to_list(persona.get("categories"))
    persona_banned = _to_list(persona.get("strictly_against"))

    ad_text_parts = [
        ad.get("title") or "",
        ad.get("description") or "",
        ad.get("tagline") or "",
        ad.get("company_persona") or "",
    ]
    ad_text = " ".join(ad_text_parts)
    ad_tokens = _tokenize(ad_text)
    ad_categories = _to_list(ad.get("categories"))
    ad_banned = _to_list(ad.get("strictly_against"))

    # Persona alignment: keyword overlap between persona text and ad text
    persona_alignment = _overlap_score(persona_tokens, ad_tokens)

    # Category match: overlap between persona preferred categories and ad categories
    category_match = _overlap_score(persona_categories, ad_categories)

    # Safety: penalize if ad contains banned terms (from persona or ad's own strictly_against)
    safety_penalty = _penalty_for_banned(persona_banned + ad_banned, ad_text)
    safety_score = max(0.0, 1.0 - safety_penalty)

    # Basic completeness: presence of key fields
    completeness = sum(bool(x) for x in [ad.get("title"), ad.get("description"), ad.get("image_url")]) / 3.0

    # Weighting and scaling to 0-100
    total = (
        persona_alignment * 0.35
        + category_match * 0.25
        + safety_score * 0.25
        + completeness * 0.15
    )

    return {
        "persona_alignment": round(persona_alignment * 100, 1),
        "category_match": round(category_match * 100, 1),
        "safety": round(safety_score * 100, 1),
        "completeness": round(completeness * 100, 1),
        "total": round(total * 100, 1),
    }


def rank_ads(ads: List[Dict[str, Any]], persona: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Score and rank ads, returning ads annotated with scores, sorted desc by total.
    """
    scored = []
    for ad in ads:
        scores = score_ad(ad, persona)
        scored.append({**ad, "scores": scores})

    scored.sort(key=lambda a: a["scores"]["total"], reverse=True)
    return scored



# ad_remixer

Server-side agent that:
- Fetches ads from Supabase (`ad_campaigns`)
- Scores them against a stored persona
- Picks the top ad and rewrites it into 3 variants with text + coherent image prompts (xAI)

## Environment

Create `auth-agents/ad_remixer/.env`:
```
XAI_API_KEY=your_xai_api_key
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key   # preferred for server fetches under RLS
# or SUPABASE_ANON_KEY if your RLS allows anon reads
```

## Supabase schema expectations

- Table `ad_campaigns` (fields used): `id,title,description,company,tagline,image_url,company_persona,strictly_against,categories,created_at`
- Optional table `personas`: `user_id, persona, strictly_against, categories` (used to fetch persona per user)

## Install deps

From repo root:
```bash
pip install -r requirements.txt
```

## Key entry points

- `supabase_client.py`
  - `get_supabase_client()` – cached client from env
  - `fetch_ads(limit=50)`
  - `fetch_persona(user_id)`

- `scoring.py`
  - `score_ad(ad, persona)` – returns per-factor scores (0–100) and total
  - `rank_ads(ads, persona)` – annotates ads with scores and sorts desc

- `agent.py` (`AdRemixerAgent`)
  - `rank_supabase_ads(user_id, context_card, limit=50)` – fetch+score ads
  - `remix_best_supabase_ad(context_card, limit=50)` – fetch+score, take top ad, generate 3 variants (text+image)
  - `remix_ads` / `remix_ads_async` – remix provided ad strings (bypass Supabase)

## Quick usage (Supabase → remix top ad)

```python
import asyncio
from ad_remixer.agent import AdRemixerAgent

context_card = {
    "user_id": "user-123",
    "user_persona_tone": "Playful, concise, startup-savvy",
    "categories": ["SaaS", "AI"],
    "strictly_against": ["gambling", "tobacco"],
}

agent = AdRemixerAgent()
result = asyncio.run(agent.remix_best_supabase_ad(context_card, limit=50))

print("Top ad scores:", result["top_ad"]["scores"])
print("Remixed variants:", [r["content"] for r in result["remixed_ads"]])
```

## Notes

- Use `SUPABASE_SERVICE_ROLE_KEY` for server-side fetches when RLS is on.
- The scorer is lightweight/deterministic; you can adjust weights in `scoring.py`.
- Images are generated via xAI tool calls inside the remix flow.


"""
Async Ensemble CTR Critic Agent
Multi-run simulation for statistically robust click-through predictions.
"""

import os
import json
import asyncio
import statistics
from dataclasses import dataclass, field
from typing import Optional
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class EnsembleCTRScore:
    """Aggregated CTR scores from multiple simulation runs."""
    ad_index: int
    ad_text: str
    
    # Mean scores
    click_prob_mean: float = 0.0
    attention_mean: float = 0.0
    relevance_mean: float = 0.0
    ctr_mean: float = 0.0
    
    # Std dev (lower = more confident)
    click_prob_std: float = 0.0
    ctr_std: float = 0.0
    
    num_runs: int = 0


@dataclass 
class EnsembleCTRPrediction:
    """Final ensemble CTR prediction."""
    user_id: str
    best_ad_index: int
    best_ad_text: str
    confidence: float
    scores: list[EnsembleCTRScore]
    total_simulations: int


class AsyncCTRCriticAgent:
    """Async ensemble CTR prediction via persona simulation."""
    
    BASE_URL = "https://api.x.ai/v1/chat/completions"
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "grok-4-1-fast-non-reasoning",
        ensemble_runs: int = 5
    ):
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY required")
        self.model = model
        self.ensemble_runs = ensemble_runs
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def _persona_prompt(self, context_card: dict) -> str:
        posts = "\n".join(f"- {post.get('text', '')}" for post in context_card.get("top_25_reranked_posts", []))
        return f"""You ARE this person:
INTERESTS: {context_card.get('general_topic', '')}
VIBE: {context_card.get('user_persona_tone', '')}
POSTS:
{posts}

React as them. Be authentic."""

    def _ctr_prompt(self, ad: str, product: str) -> str:
        return f"""Ad for "{product}":
"{ad}"

Would you click? JSON only:
{{"click_probability": <0-1>, "attention_score": <0-1>, "relevance_score": <0-1>}}"""

    async def _eval_once(
        self, 
        client: httpx.AsyncClient,
        ad: str, 
        product: str, 
        context_card: dict,
        temp: float
    ) -> dict:
        """Single async CTR evaluation."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._persona_prompt(context_card)},
                {"role": "user", "content": self._ctr_prompt(ad, product)}
            ],
            "temperature": temp,
            "max_tokens": 100
        }
        
        try:
            r = await client.post(self.BASE_URL, json=payload, headers=self.headers)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"].strip()
            if "```" in content:
                content = content.split("```")[1].replace("json", "").strip()
            return json.loads(content)
        except Exception:
            return {"click_probability": 0.5, "attention_score": 0.5, "relevance_score": 0.5}

    async def _ensemble_eval(
        self,
        client: httpx.AsyncClient,
        ad: str,
        ad_idx: int,
        product: str,
        context_card: dict
    ) -> EnsembleCTRScore:
        """Run multiple simulations for one ad."""
        temps = [0.5 + (i * 0.15) for i in range(self.ensemble_runs)]
        
        results = await asyncio.gather(*[
            self._eval_once(client, ad, product, context_card, t) for t in temps
        ])
        
        clicks = [r["click_probability"] for r in results]
        attns = [r["attention_score"] for r in results]
        rels = [r["relevance_score"] for r in results]
        ctrs = [c * 0.5 + a * 0.3 + r * 0.2 for c, a, r in zip(clicks, attns, rels)]
        
        def safe_std(v): return statistics.stdev(v) if len(v) > 1 else 0.0
        
        return EnsembleCTRScore(
            ad_index=ad_idx,
            ad_text=ad,
            click_prob_mean=statistics.mean(clicks),
            attention_mean=statistics.mean(attns),
            relevance_mean=statistics.mean(rels),
            ctr_mean=statistics.mean(ctrs),
            click_prob_std=safe_std(clicks),
            ctr_std=safe_std(ctrs),
            num_runs=len(results)
        )

    async def predict_async(self, context_card: dict, remixed_ads: dict, product: str = "") -> EnsembleCTRPrediction:
        """Run full ensemble CTR prediction."""
        user_id = remixed_ads.get("user_id", context_card.get("username", "unknown"))
        ads = remixed_ads.get("rewritten_ads", [])
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            scores = await asyncio.gather(*[
                self._ensemble_eval(client, ad, idx, product, context_card)
                for idx, ad in enumerate(ads)
            ])
        
        scores = sorted(scores, key=lambda x: x.ctr_mean, reverse=True)
        
        # Confidence: gap + consistency
        confidence = 0.7
        if len(scores) >= 2:
            gap = scores[0].ctr_mean - scores[1].ctr_mean
            consistency = 1 - min(scores[0].ctr_std * 2, 0.4)
            confidence = min((0.4 + gap * 2) * consistency + 0.2, 0.95)
        
        return EnsembleCTRPrediction(
            user_id=user_id,
            best_ad_index=scores[0].ad_index,
            best_ad_text=scores[0].ad_text,
            confidence=confidence,
            scores=scores,
            total_simulations=sum(s.num_runs for s in scores)
        )

    def predict(self, context_card: dict, remixed_ads: dict, product: str = "") -> EnsembleCTRPrediction:
        """Sync wrapper."""
        return asyncio.run(self.predict_async(context_card, remixed_ads, product))


if __name__ == "__main__":
    # Load context card JSON file
    context_card_path = "../x_auth/user_data_xhardiksr_1997090614605934592_context_card.json"
    with open(context_card_path, "r") as f:
        context_card = json.load(f)
    
    # Load remixed ads output JSON file
    remixed_ads_path = "../ad_remixer/remixed_ads_output.json"
    with open(remixed_ads_path, "r") as f:
        remixed_ads = json.load(f)
    
    # Product name (can be extracted from remixed ads or passed separately)
    # product = "ZetaBook Pro"  # Extract from remixed ads or pass as parameter
    
    critic = AsyncCTRCriticAgent(ensemble_runs=10)
    result = critic.predict(context_card, remixed_ads, product)
    
    print(f"\n{'='*55}")
    print(f"ENSEMBLE CTR PREDICTION | {result.total_simulations} simulations")
    print(f"{'='*55}")
    print(f"\n🏆 BEST: Ad #{result.best_ad_index} | Confidence: {result.confidence:.1%}")
    print(f'   "{result.best_ad_text}"')
    
    print(f"\n{'─'*55}")
    for i, s in enumerate(result.scores, 1):
        print(f"#{i} Ad[{s.ad_index}] CTR={s.ctr_mean:.3f}±{s.ctr_std:.3f} | click={s.click_prob_mean:.2f} attn={s.attention_mean:.2f}")

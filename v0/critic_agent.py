"""
Async Ensemble CTR Critic Agent
Multi-run simulation for statistically robust click-through predictions.
"""

import json
import asyncio
import statistics
from dataclasses import dataclass, field
from typing import Optional, List, Union
import httpx

from config import XAI_API_KEY, DEFAULT_MODEL, CTR_ENSEMBLE_RUNS


@dataclass
class EnsembleCTRScore:
    """Aggregated CTR scores from multiple simulation runs."""
    ad_index: int
    ad_text: str
    
    click_prob_mean: float = 0.0
    attention_mean: float = 0.0
    relevance_mean: float = 0.0
    ctr_mean: float = 0.0
    
    click_prob_std: float = 0.0
    ctr_std: float = 0.0
    
    num_runs: int = 0
    
    def to_dict(self) -> dict:
        return {
            "ad_index": self.ad_index,
            "ad_text": self.ad_text,
            "click_prob_mean": self.click_prob_mean,
            "attention_mean": self.attention_mean,
            "relevance_mean": self.relevance_mean,
            "ctr_mean": self.ctr_mean,
            "click_prob_std": self.click_prob_std,
            "ctr_std": self.ctr_std,
            "num_runs": self.num_runs
        }


@dataclass 
class CTRPredictionResult:
    """Final ensemble CTR prediction."""
    user_id: str
    best_ad_index: int
    best_ad_text: str
    confidence: float
    scores: List[EnsembleCTRScore] = field(default_factory=list)
    total_simulations: int = 0
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "best_ad_index": self.best_ad_index,
            "best_ad_text": self.best_ad_text,
            "confidence": self.confidence,
            "scores": [s.to_dict() for s in self.scores],
            "total_simulations": self.total_simulations
        }


class CTRCriticAgent:
    """Async ensemble CTR prediction via persona simulation."""
    
    BASE_URL = "https://api.x.ai/v1/chat/completions"
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = None,
        ensemble_runs: int = None
    ):
        self.api_key = api_key or XAI_API_KEY
        if not self.api_key:
            raise ValueError("XAI_API_KEY required")
        self.model = model or DEFAULT_MODEL
        self.ensemble_runs = ensemble_runs or CTR_ENSEMBLE_RUNS
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def _persona_prompt(self, context_card: dict) -> str:
        posts = context_card.get("top_25_reranked_posts", [])
        posts_text = "\n".join(f"- {post.get('text', '')}" for post in posts)
        return f"""You ARE this person:
INTERESTS: {context_card.get('general_topic', '')}
VIBE: {context_card.get('user_persona_tone', '')}
POSTS:
{posts_text}

React as them. Be authentic."""

    def _extract_product_prompt(self, ads: list) -> str:
        """Prompt for extracting product name from ads."""
        ads_text = "\n".join([f"- {ad}" for ad in ads])
        return f"""Given these ads:
{ads_text}

Extract the product name being advertised. Return ONLY the product name, nothing else."""

    async def _extract_product(self, client: httpx.AsyncClient, remixed_ads: dict) -> str:
        """Extract product name from remixed ads using Grok."""
        ads = remixed_ads.get("rewritten_ads", [])
        if not ads:
            return ""
        
        # Handle both dict format and AdVariant format
        ad_texts = []
        for ad in ads:
            if isinstance(ad, dict):
                ad_texts.append(ad.get("content", ""))
            elif hasattr(ad, 'content'):
                ad_texts.append(ad.content)
            else:
                ad_texts.append(str(ad))
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": self._extract_product_prompt(ad_texts)}
            ],
            "temperature": 0.3,
            "max_tokens": 50
        }
        
        try:
            r = await client.post(self.BASE_URL, json=payload, headers=self.headers)
            r.raise_for_status()
            product = r.json()["choices"][0]["message"]["content"].strip()
            return product.strip('"\'')
        except Exception:
            return ""

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

    async def predict_async(
        self, 
        context_card: Union[dict, 'ContextCard'], 
        remixed_ads: Union[dict, 'RemixedAdsResult'], 
        product: str = ""
    ) -> CTRPredictionResult:
        """
        Run full ensemble CTR prediction.
        
        Args:
            context_card: User context card
            remixed_ads: Remixed ads result
            product: Optional product name (extracted automatically if not provided)
            
        Returns:
            CTRPredictionResult with best ad and scores
        """
        # Convert to dicts if needed
        if hasattr(context_card, 'to_dict'):
            context_card = context_card.to_dict()
        if hasattr(remixed_ads, 'to_dict'):
            remixed_ads = remixed_ads.to_dict()
        
        user_id = remixed_ads.get("user_id", context_card.get("username", "unknown"))
        ads_data = remixed_ads.get("rewritten_ads", [])
        
        # Extract ad texts
        ads = []
        for ad in ads_data:
            if isinstance(ad, dict):
                ads.append(ad.get("content", ""))
            elif hasattr(ad, 'content'):
                ads.append(ad.content)
            else:
                ads.append(str(ad))
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            if not product:
                product = await self._extract_product(client, remixed_ads)
            
            scores = await asyncio.gather(*[
                self._ensemble_eval(client, ad, idx, product, context_card)
                for idx, ad in enumerate(ads)
            ])
        
        scores = sorted(scores, key=lambda x: x.ctr_mean, reverse=True)
        
        # Calculate confidence
        confidence = 0.7
        if len(scores) >= 2:
            gap = scores[0].ctr_mean - scores[1].ctr_mean
            consistency = 1 - min(scores[0].ctr_std * 2, 0.4)
            confidence = min((0.4 + gap * 2) * consistency + 0.2, 0.95)
        
        return CTRPredictionResult(
            user_id=user_id,
            best_ad_index=scores[0].ad_index,
            best_ad_text=scores[0].ad_text,
            confidence=confidence,
            scores=list(scores),
            total_simulations=sum(s.num_runs for s in scores)
        )

    def predict(
        self, 
        context_card: Union[dict, 'ContextCard'], 
        remixed_ads: Union[dict, 'RemixedAdsResult'], 
        product: str = ""
    ) -> CTRPredictionResult:
        """Sync wrapper for predict_async."""
        return asyncio.run(self.predict_async(context_card, remixed_ads, product))


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        context_file = sys.argv[1]
        remixed_file = sys.argv[2]
        
        print(f"Loading context card from {context_file}...")
        with open(context_file, "r") as f:
            context_card = json.load(f)
        
        print(f"Loading remixed ads from {remixed_file}...")
        with open(remixed_file, "r") as f:
            remixed_ads = json.load(f)
        
        print("Running CTR prediction...")
        critic = CTRCriticAgent()
        result = critic.predict(context_card, remixed_ads)
        
        print(f"\n{'='*55}")
        print(f"ENSEMBLE CTR PREDICTION | {result.total_simulations} simulations")
        print(f"{'='*55}")
        print(f"\n🏆 BEST: Ad #{result.best_ad_index} | Confidence: {result.confidence:.1%}")
        print(f'   "{result.best_ad_text[:80]}..."')
        
        print(f"\n{'─'*55}")
        for i, s in enumerate(result.scores, 1):
            print(f"#{i} Ad[{s.ad_index}] CTR={s.ctr_mean:.3f}±{s.ctr_std:.3f} | click={s.click_prob_mean:.2f} attn={s.attention_mean:.2f}")
    else:
        print("Usage: python critic_agent.py <context_card.json> <remixed_ads.json>")

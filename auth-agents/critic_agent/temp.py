"""
Async Ensemble CTR Critic Agent
Multi-run simulation for statistically robust click-through predictions.
"""

import os
import json
import asyncio
import statistics
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
from xai_sdk import AsyncClient
from xai_sdk.chat import system, user

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
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "grok-4-1-fast-non-reasoning",
        ensemble_runs: int = 5
    ):
        # Load API key from .env file if not provided
        if api_key is None:
            api_key = os.getenv("XAI_API_KEY")
            if not api_key:
                raise ValueError("XAI_API_KEY not found. Set it in .env file or pass as api_key parameter.")
        
        self.client = AsyncClient(api_key=api_key)
        self.model = model
        self.ensemble_runs = ensemble_runs

    def _persona_prompt(self, persona: dict) -> str:
        posts = "\n".join(f"- {p}" for p in persona.get("context", []))
        return f"""You ARE this person:
INTERESTS: {persona.get('fav_topic')}
VIBE: {persona.get('tone')}
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
        ad: str, 
        product: str, 
        persona: dict,
        temp: float
    ) -> dict:
        """Single async CTR evaluation."""
        content = ""
        try:
            # Create a chat instance with system and user messages
            chat = self.client.chat.create(
                model=self.model,
                messages=[
                    system(self._persona_prompt(persona)),
                    user(self._ctr_prompt(ad, product))
                ],
                temperature=temp,
                max_tokens=100
            )
            
            # Get response
            response = await chat.sample()
            content = response.content.strip()
            
            # Clean up JSON if wrapped in code blocks
            if "```" in content:
                # Handle both ```json and ``` cases
                parts = content.split("```")
                for part in parts:
                    part = part.replace("json", "").strip()
                    if part.startswith("{") and part.endswith("}"):
                        content = part
                        break
            
            result = json.loads(content)
            # Validate the result has the expected keys
            if not all(k in result for k in ["click_probability", "attention_score", "relevance_score"]):
                raise ValueError("Missing required keys in response")
            return result
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}, content: {content[:100] if content else 'empty'}")
            return {"click_probability": 0.5, "attention_score": 0.5, "relevance_score": 0.5}
        except Exception as e:
            print(f"Error in _eval_once: {type(e).__name__}: {e}")
            if content:
                print(f"  Response content: {content[:200]}")
            return {"click_probability": 0.5, "attention_score": 0.5, "relevance_score": 0.5}

    async def _ensemble_eval(
        self,
        ad: str,
        ad_idx: int,
        product: str,
        persona: dict
    ) -> EnsembleCTRScore:
        """Run multiple simulations for one ad."""
        temps = [0.5 + (i * 0.15) for i in range(self.ensemble_runs)]
        
        results = await asyncio.gather(*[
            self._eval_once(ad, product, persona, t) for t in temps
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

    async def predict_async(self, user_data: dict, persona: dict) -> EnsembleCTRPrediction:
        """Run full ensemble CTR prediction."""
        user_id = user_data.get("user_id", "unknown")
        product = user_data.get("product", "")
        ads = user_data.get("suggested_ads", [])
        
        # Run all evaluations concurrently
        scores = await asyncio.gather(*[
            self._ensemble_eval(ad, idx, product, persona)
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

    async def close(self):
        """Close the async client properly."""
        # The AsyncClient uses gRPC which handles cleanup automatically
        # But we can ensure the underlying channel is closed if needed
        pass

    def predict(self, user_data: dict, persona: dict) -> EnsembleCTRPrediction:
        """Sync wrapper with proper cleanup."""
        async def run():
            try:
                return await self.predict_async(user_data, persona)
            finally:
                # Ensure client is properly closed
                await self.close()
        
        # Use asyncio.run which properly handles cleanup
        return asyncio.run(run())


if __name__ == "__main__":
    user_data = {
        "user_id": "user_008",
        "product": "Gentle 7-day screen-time reset program",
        "suggested_ads": [
        "did a quiet 7-day digital detox thing and remembered sunsets are free. turns out the world is still kinda beautiful",
        "spent a week with limited phone and actually called friends with my voice. felt weirdly human again",
        "no preaching just gentle daily nudges. came back calmer and kept most of the habits. small quiet glow-up"
        ]
    }
    
    persona = {
        "user_id": "user_008",
        "fav_topic": "wholesome & anti-doomer",
        "tone": "genuinely positive, anti-cope, warm but not cringe",
        "context": [
        "told my dad i loved him today. he cried. do it coward",
        "helped an old lady with groceries and she called me a good boy. injecting this dopamine directly into my veins",
        "deleted twitter for 3 days and remembered birds exist",
        "gym pb + made someone laugh + didn’t doomscroll before bed. triple threat",
        "called my mom just to say hi and she said she was proud of me. brb crying",
        "sunset was beautiful today. no filter needed",
        "told my friend i was struggling and he just showed up with beer and silence. real one",
        "ate vegetables and didn’t hate myself. small victories",
        "life’s actually not that bad when you log off and touch grass",
        "be the light you want to see in the timeline"
        ]
    }
    
    async def main():
        critic = AsyncCTRCriticAgent(ensemble_runs=10)
        try:
            result = await critic.predict_async(user_data, persona)
            
            print(f"\n{'='*55}")
            print(f"ENSEMBLE CTR PREDICTION | {result.total_simulations} simulations")
            print(f"{'='*55}")
            print(f"\n🏆 BEST: Ad #{result.best_ad_index} | Confidence: {result.confidence:.1%}")
            print(f'   "{result.best_ad_text}"')
            
            print(f"\n{'─'*55}")
            for i, s in enumerate(result.scores, 1):
                print(f"#{i} Ad[{s.ad_index}] CTR={s.ctr_mean:.3f}±{s.ctr_std:.3f} | click={s.click_prob_mean:.2f} attn={s.attention_mean:.2f}")
        finally:
            await critic.close()
    
    asyncio.run(main())
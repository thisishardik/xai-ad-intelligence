"""
Ad Intelligence Pipeline
Orchestrates the full flow: Auth → Context → Remix → Critic

Usage:
    # Interactive mode (runs OAuth flow)
    python pipeline.py
    
    # With existing user data JSON
    python pipeline.py user_data.json
    
    # With existing context card (skips auth and context generation)
    python pipeline.py --context context_card.json

Supabase:
- Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or ANON key if RLS permits)
- Ads are fetched from Supabase ad_campaigns; no default/fallback ads are used
"""

import json
import argparse
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path

from config import validate_config
from auth_client import AuthClient, UserData, interactive_auth
from context_agent import ContextAgent, ContextCard
from ad_remixer import AdRemixerAgent, RemixedAdsResult
from critic_agent import CTRCriticAgent, CTRPredictionResult


@dataclass
class PipelineResult:
    """Complete pipeline result."""
    user_id: str
    username: str
    context_card: ContextCard
    remixed_ads: RemixedAdsResult
    ctr_prediction: CTRPredictionResult
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "context_card": self.context_card.to_dict(),
            "remixed_ads": self.remixed_ads.to_dict(),
            "ctr_prediction": self.ctr_prediction.to_dict()
        }


class AdIntelligencePipeline:
    """
    Complete Ad Intelligence Pipeline.
    
    Runs the full flow:
    1. Auth: Authenticate with X and fetch user data
    2. Context: Analyze user data and create context card
    3. Remix: Select best ad and generate 3 personalized variants
    4. Critic: Predict CTR for each variant
    """
    
    def __init__(self, ads: Optional[List[str]] = None):
        """
        Initialize the pipeline.
        
        Args:
            ads: Optional list of candidate ads. If None, ads are fetched from Supabase.
        """
        validate_config()
        
        self.ads = ads
        self.context_agent = ContextAgent()
        self.remixer_agent = AdRemixerAgent()
        self.critic_agent = CTRCriticAgent()
    
    def run_from_auth(self) -> PipelineResult:
        """
        Run the full pipeline starting with OAuth authentication.
        
        This will:
        1. Prompt user to authenticate via browser
        2. Fetch their X data (posts, timeline, likes, bookmarks)
        3. Analyze and create context card
        4. Remix ads to match their style
        5. Predict CTR for each variant
        
        Returns:
            PipelineResult with all outputs
        """
        print("\n" + "="*60)
        print("AD INTELLIGENCE PIPELINE")
        print("="*60)
        
        # Step 1: Auth
        print("\n📱 STEP 1: Authentication")
        print("-"*40)
        user_data = interactive_auth()
        
        return self._run_from_user_data(user_data)
    
    def run_from_user_data(self, user_data: dict) -> PipelineResult:
        """
        Run the pipeline from existing user data.
        
        Args:
            user_data: Dict with posts, timeline, likes, bookmarks
            
        Returns:
            PipelineResult with all outputs
        """
        print("\n" + "="*60)
        print("AD INTELLIGENCE PIPELINE")
        print("="*60)
        
        # Convert dict to UserData if needed
        if isinstance(user_data, dict):
            ud = UserData(
                user_id=user_data.get("user_id", "unknown"),
                username=user_data.get("username", "unknown"),
                posts=user_data.get("posts", []),
                timeline=user_data.get("timeline", []),
                likes=user_data.get("likes", []),
                bookmarks=user_data.get("bookmarks", [])
            )
        else:
            ud = user_data
        
        return self._run_from_user_data(ud)
    
    def _run_from_user_data(self, user_data: UserData) -> PipelineResult:
        """Internal method to run pipeline from UserData."""
        
        # Step 2: Context Generation
        print("\n🎯 STEP 2: Context Analysis")
        print("-"*40)
        print(f"  Analyzing user @{user_data.username}...")
        context_card = self.context_agent.create_context_card(user_data.to_dict())
        print(f"  ✓ Topic: {context_card.general_topic}")
        print(f"  ✓ Tone: {context_card.user_persona_tone}")
        print(f"  ✓ Posts analyzed: {len(context_card.top_25_reranked_posts)}")
        
        return self._run_from_context_card(context_card, user_data.user_id, user_data.username)
    
    def run_from_context_card(self, context_card: dict) -> PipelineResult:
        """
        Run the pipeline from an existing context card.
        
        Args:
            context_card: Dict with user persona analysis
            
        Returns:
            PipelineResult with all outputs
        """
        print("\n" + "="*60)
        print("AD INTELLIGENCE PIPELINE (from context card)")
        print("="*60)
        
        # Convert to ContextCard if needed
        if isinstance(context_card, dict):
            from context_agent import RerankedPost
            posts = [
                RerankedPost(
                    post_id=p.get("post_id", ""),
                    text=p.get("text", ""),
                    source=p.get("source", ""),
                    rank=p.get("rank", 0),
                    relevance_score=p.get("relevance_score", 0.5)
                )
                for p in context_card.get("top_25_reranked_posts", [])
            ]
            cc = ContextCard(
                username=context_card.get("username", "unknown"),
                user_id=context_card.get("user_id", context_card.get("username", "unknown")),
                general_topic=context_card.get("general_topic", ""),
                popular_memes=context_card.get("popular_memes"),
                user_persona_tone=context_card.get("user_persona_tone", ""),
                top_25_reranked_posts=posts
            )
        else:
            cc = context_card
        
        return self._run_from_context_card(cc, cc.user_id, cc.username)
    
    def _run_from_context_card(
        self, 
        context_card: ContextCard, 
        user_id: str, 
        username: str
    ) -> PipelineResult:
        """Internal method to run pipeline from ContextCard."""
        
        # Step 3: Ad Remixing
        print("\n🎨 STEP 3: Ad Remixing")
        print("-"*40)
        print("  Fetching ads from Supabase and ranking against persona...")
        remixed_ads = self.remixer_agent.remix_ads(context_card, self.ads, log_ranking=True)
        print(f"  ✓ Selected: {remixed_ads.selected_ad[:50]}... (reason: {remixed_ads.selection_reasoning})")
        print(f"  ✓ Generated {len(remixed_ads.rewritten_ads)} variants")
        
        # Step 4: CTR Prediction
        print("\n📊 STEP 4: CTR Prediction")
        print("-"*40)
        print(f"  Running ensemble simulations...")
        ctr_prediction = self.critic_agent.predict(context_card, remixed_ads)
        print(f"  ✓ Simulations: {ctr_prediction.total_simulations}")
        print(f"  ✓ Best Ad: #{ctr_prediction.best_ad_index}")
        print(f"  ✓ Confidence: {ctr_prediction.confidence:.1%}")
        
        result = PipelineResult(
            user_id=user_id,
            username=username,
            context_card=context_card,
            remixed_ads=remixed_ads,
            ctr_prediction=ctr_prediction
        )
        
        self._print_summary(result)
        
        return result
    
    def _print_summary(self, result: PipelineResult):
        """Print a summary of the pipeline results."""
        print("\n" + "="*60)
        print("PIPELINE RESULTS SUMMARY")
        print("="*60)
        
        print(f"\n👤 User: @{result.username} ({result.user_id})")
        print(f"📌 Interests: {result.context_card.general_topic}")
        print(f"🎭 Tone: {result.context_card.user_persona_tone}")
        
        print(f"\n🎯 Selected Original Ad:")
        print(f'   "{result.remixed_ads.selected_ad}"')
        print(f"   Reason: {result.remixed_ads.selection_reasoning}")
        
        print(f"\n🏆 BEST PERFORMING AD (#{result.ctr_prediction.best_ad_index}):")
        print(f'   "{result.ctr_prediction.best_ad_text}"')
        print(f"   Confidence: {result.ctr_prediction.confidence:.1%}")
        
        print("\n📊 All Variants:")
        for i, score in enumerate(result.ctr_prediction.scores):
            variant = result.remixed_ads.rewritten_ads[score.ad_index]
            marker = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
            print(f"\n   {marker} Variant {score.ad_index + 1}:")
            print(f'      "{variant.content[:80]}..."')
            print(f"      CTR: {score.ctr_mean:.3f} ± {score.ctr_std:.3f}")
            if variant.image_uri:
                print(f"      Image: {variant.image_uri}")


def save_results(result: PipelineResult, output_dir: str = "."):
    """Save pipeline results to JSON files."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{result.username}_{timestamp}"
    
    # Save individual files
    files = {
        f"{base_name}_context_card.json": result.context_card.to_dict(),
        f"{base_name}_remixed_ads.json": result.remixed_ads.to_dict(),
        f"{base_name}_ctr_prediction.json": result.ctr_prediction.to_dict(),
        f"{base_name}_full_result.json": result.to_dict()
    }
    
    for filename, data in files.items():
        filepath = output_path / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Results saved to {output_dir}/")
    for filename in files:
        print(f"   - {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Ad Intelligence Pipeline - Personalized ad generation with CTR prediction"
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Path to user data JSON file (optional - runs interactive auth if not provided)"
    )
    parser.add_argument(
        "--context",
        help="Path to existing context card JSON (skips auth and context generation)"
    )
    parser.add_argument(
        "--ads",
        help="Path to JSON file containing list of candidate ads"
    )
    parser.add_argument(
        "--output",
        default=".",
        help="Output directory for results (default: current directory)"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to files"
    )
    
    args = parser.parse_args()
    
    # Load custom ads if provided
    custom_ads = None
    if args.ads:
        with open(args.ads, 'r') as f:
            custom_ads = json.load(f)
    
    # Initialize pipeline
    pipeline = AdIntelligencePipeline(ads=custom_ads)
    
    # Run appropriate pipeline path
    if args.context:
        # Run from existing context card
        print(f"Loading context card from {args.context}...")
        with open(args.context, 'r', encoding='utf-8') as f:
            context_card = json.load(f)
        result = pipeline.run_from_context_card(context_card)
    elif args.input_file:
        # Run from existing user data
        print(f"Loading user data from {args.input_file}...")
        with open(args.input_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
        result = pipeline.run_from_user_data(user_data)
    else:
        # Run full pipeline with interactive auth
        result = pipeline.run_from_auth()
    
    # Save results
    if not args.no_save:
        save_results(result, args.output)
    
    return result


if __name__ == "__main__":
    main()

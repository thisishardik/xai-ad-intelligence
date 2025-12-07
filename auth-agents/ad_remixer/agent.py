"""
Ad Remixer Agent
Takes user context card and list of ads, picks the best ad, and rewrites it 
into 3 parallel versions matching the user's style from top_25_reranked_posts.
"""

import os
import json
import asyncio
from typing import Optional, List
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class AdRemixerAgent:
    """Agent that remixes ads to match user's style."""
    
    BASE_URL = "https://api.x.ai/v1/chat/completions"
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "grok-4-1-fast"
    ):
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY required")
        self.model = model
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def _build_style_reference(self, context_card: dict) -> str:
        """Build style reference from top_25_reranked_posts."""
        posts = context_card.get("top_25_reranked_posts", [])
        if not posts:
            return "No style reference available."
        
        # Extract text from posts
        post_texts = [post.get("text", "") for post in posts[:25]]
        style_examples = "\n".join([f"- {text}" for text in post_texts if text])
        
        return f"""USER STYLE REFERENCE (top 25 posts from their posts, timeline, likes, and bookmarks):
{style_examples}

PERSONA: {context_card.get('user_persona_tone', 'unknown')}
INTERESTS: {context_card.get('general_topic', 'unknown')}"""

    def _ad_selection_prompt(self, ads: List[str], context_card: dict) -> str:
        """Prompt for selecting the best ad."""
        style_ref = self._build_style_reference(context_card)
        
        ads_list = "\n".join([f"{i+1}. {ad}" for i, ad in enumerate(ads)])
        
        return f"""{style_ref}

CANDIDATE ADS:
{ads_list}

Select the ad most aligned with this user's interests and content engagement patterns.

Return JSON only:
{{
    "selected_ad_index": <0-based index>,
    "selected_ad_text": "<exact ad text>",
    "reasoning": "<1 sentence>"
}}"""

    def _ad_rewrite_prompt(self, ad: str, context_card: dict, variant_num: int) -> str:
        """Prompt for rewriting an ad in user's style."""
        style_ref = self._build_style_reference(context_card)
        
        # Different creative directions for each variant
        variant_instructions = {
            1: "Focus on their most casual, conversational style. Use their typical slang and informal tone.",
            2: "Match their authentic voice but emphasize the core benefit more directly.",
            3: "Channel their personality but take a slightly different angle or hook on the message."
        }
        
        variation = variant_instructions.get(variant_num, variant_instructions[1])
        
        return f"""{style_ref}

ORIGINAL AD:
"{ad}"

Rewrite this ad to match the user's style. {variation}
Make it sound like THEY wrote it based on the examples above.

Return ONLY the rewritten ad text. No quotes, no explanations."""

    async def _select_best_ad(
        self,
        client: httpx.AsyncClient,
        ads: List[str],
        context_card: dict
    ) -> dict:
        """Select the best ad from the list."""
        prompt = self._ad_selection_prompt(ads, context_card)
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert at analyzing user preferences and selecting the most suitable content. Return only valid JSON."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        try:
            r = await client.post(self.BASE_URL, json=payload, headers=self.headers)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"].strip()
            
            # Extract JSON if wrapped in code blocks
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            return result
        except Exception as e:
            print(f"Error selecting ad: {e}")
            # Fallback to first ad
            return {
                "selected_ad_index": 0,
                "selected_ad_text": ads[0] if ads else "",
                "reasoning": "Fallback due to error"
            }

    async def _rewrite_ad_variant(
        self,
        client: httpx.AsyncClient,
        ad: str,
        context_card: dict,
        variant_num: int
    ) -> str:
        """Rewrite an ad in one style variant."""
        prompt = self._ad_rewrite_prompt(ad, context_card, variant_num)
        
        # Different temperatures for diversity: variant 1 = 0.7, variant 2 = 0.9, variant 3 = 1.1
        temperature = 0.5 + (variant_num * 0.2)
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert at rewriting content to match specific writing styles. Return only the rewritten text, no explanations."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": 500
        }
        
        try:
            r = await client.post(self.BASE_URL, json=payload, headers=self.headers)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"].strip()
            
            # Clean up if wrapped in quotes or code blocks
            content = content.strip('"').strip("'")
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            
            return content.strip()
        except Exception as e:
            print(f"Error rewriting ad variant {variant_num}: {e}")
            return ad  # Fallback to original

    async def remix_ads_async(
        self,
        context_card: dict,
        ads: List[str]
    ) -> dict:
        """Main async method to remix ads."""
        if not ads:
            raise ValueError("At least one ad is required")
        
        if len(ads) > 5:
            ads = ads[:5]  # Limit to 5 ads
        
        # Extract user_id (prefer user_id, fallback to username)
        user_id = context_card.get("user_id") or context_card.get("username", "unknown")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: Select the best ad
            selection = await self._select_best_ad(client, ads, context_card)
            selected_ad = selection.get("selected_ad_text", ads[0])
            
            # Step 2: Rewrite the selected ad into 3 parallel variants (multi-threaded async calls)
            rewritten_ads = await asyncio.gather(*[
                self._rewrite_ad_variant(client, selected_ad, context_card, i+1)
                for i in range(3)
            ])
        
        return {
            "user_id": user_id,
            "rewritten_ads": rewritten_ads
        }

    def remix_ads(
        self,
        context_card: dict,
        ads: List[str]
    ) -> dict:
        """Sync wrapper for remix_ads_async."""
        return asyncio.run(self.remix_ads_async(context_card, ads))


if __name__ == "__main__":
    # Example usage
    import sys
    
    # Load context card
    if len(sys.argv) > 1:
        context_card_file = sys.argv[1]
    else:
        context_card_file = "user_data_DotVignesh_1009524384351096833_context_card.json"
    
    print(f"Loading context card from {context_card_file}...")
    with open(context_card_file, 'r', encoding='utf-8') as f:
        context_card = json.load(f)
    
    # Example ads (in real usage, these would come from another system)
    example_ads = [
        "Upgrade to the new ZetaBook Pro for unmatched speed and seamless multitasking.",
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
    
    print("\nRemixing ads...")
    agent = AdRemixerAgent()
    result = agent.remix_ads(context_card, example_ads)
    
    print("\n" + "="*60)
    print("AD REMIX RESULTS")
    print("="*60)
    print(f"\nUser ID: {result['user_id']}")
    print(f"\nRewritten Ads ({len(result['rewritten_ads'])} variants):")
    print("-" * 60)
    for i, ad in enumerate(result['rewritten_ads'], 1):
        print(f"\nVariant {i}:")
        print(f'"{ad}"')
    
    # Save to JSON
    output_file = "remixed_ads_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n\nResults saved to: {output_file}")

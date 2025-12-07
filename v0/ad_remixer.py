"""
Ad Remixer Agent
Takes user context card and list of ads, picks the best ad, and rewrites it 
into 3 parallel versions matching the user's style.

Uses xai_sdk with tool calling to coherently generate ad text and images together.
"""

import json
from typing import Optional, List, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from xai_sdk import Client
from xai_sdk.chat import user, system, tool, tool_result

from config import XAI_API_KEY, DEFAULT_MODEL, IMAGE_MODEL, DEFAULT_ADS


@dataclass
class AdVariant:
    """A single ad variant with copy and optional image."""
    content: str
    image_uri: Optional[str] = None
    image_prompt: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "image_uri": self.image_uri,
            "image_prompt": self.image_prompt
        }


@dataclass 
class RemixedAdsResult:
    """Result of ad remixing."""
    user_id: str
    selected_ad: str
    selection_reasoning: str
    rewritten_ads: List[AdVariant] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "selected_ad": self.selected_ad,
            "selection_reasoning": self.selection_reasoning,
            "rewritten_ads": [ad.to_dict() for ad in self.rewritten_ads]
        }


def create_image_generation_tool():
    """Create the image generation tool definition."""
    return tool(
        name="generate_ad_image",
        description="Generate a compelling visual image for the ad. Call this AFTER you've written the ad copy to create a coherent image that complements the text.",
        parameters={
            "type": "object",
            "properties": {
                "image_prompt": {
                    "type": "string",
                    "description": "A detailed prompt describing the image to generate. Include style, mood, colors, composition, and key visual elements that align with the ad copy."
                },
                "ad_copy": {
                    "type": "string",
                    "description": "The final ad copy text that this image should complement."
                }
            },
            "required": ["image_prompt", "ad_copy"]
        }
    )


class AdRemixerAgent:
    """Agent that remixes ads to match user's style using coherent text+image generation."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = None,
        image_model: str = None
    ):
        self.api_key = api_key or XAI_API_KEY
        if not self.api_key:
            raise ValueError("XAI_API_KEY required")
        self.model = model or DEFAULT_MODEL
        self.image_model = image_model or IMAGE_MODEL
        self.client = Client(api_key=self.api_key)
        self.image_tool = create_image_generation_tool()

    def _build_style_reference(self, context_card: Union[dict, 'ContextCard']) -> str:
        """Build style reference from top_25_reranked_posts."""
        # Handle both dict and ContextCard
        if hasattr(context_card, 'to_dict'):
            context_card = context_card.to_dict()
        
        posts = context_card.get("top_25_reranked_posts", [])
        if not posts:
            return "No style reference available."
        
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
        """Prompt for rewriting an ad in user's style with coherent image generation."""
        style_ref = self._build_style_reference(context_card)
        
        variant_instructions = {
            1: "Focus on their most casual, conversational style. Use their typical slang and informal tone. Image should feel authentic and relatable.",
            2: "Match their authentic voice but emphasize the core benefit more directly. Image should highlight the key value proposition.",
            3: "Channel their personality but take a slightly different angle or hook on the message. Image should be eye-catching and memorable."
        }
        
        variation = variant_instructions.get(variant_num, variant_instructions[1])
        
        return f"""{style_ref}

ORIGINAL AD:
"{ad}"

Your task:
1. Rewrite this ad to match the user's style. {variation}
   Make it sound like THEY wrote it based on the examples above.

2. After writing the ad copy, use the generate_ad_image tool to create a visual that perfectly complements your ad copy.
   - The image should reinforce the message
   - Match the tone and style of the copy
   - Be visually compelling for social media

Think about the ad copy and image as a unified creative unit - they should work together to deliver the message."""

    def _select_best_ad(self, ads: List[str], context_card: dict) -> dict:
        """Select the best ad from the list using xai_sdk."""
        prompt = self._ad_selection_prompt(ads, context_card)
        
        chat = self.client.chat.create(
            model=self.model,
            messages=[
                system("You are an expert at analyzing user preferences and selecting suitable content. Return only valid JSON."),
                user(prompt)
            ],
            temperature=0.3,
        )
        
        try:
            response = chat.sample()
            content = response.content.strip()
            
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            return json.loads(content)
        except Exception as e:
            print(f"Error selecting ad: {e}")
            return {
                "selected_ad_index": 0,
                "selected_ad_text": ads[0] if ads else "",
                "reasoning": "Fallback due to error"
            }

    def _generate_ad_image(self, image_prompt: str) -> Optional[str]:
        """Generate an image using xai_sdk image generation."""
        try:
            response = self.client.image.sample(
                model=self.image_model,
                prompt=image_prompt,
                image_format="url"
            )
            
            if hasattr(response, 'url'):
                return response.url
            return None
        except Exception as e:
            print(f"Error generating image: {e}")
            return None

    def _rewrite_ad_variant(
        self,
        ad: str,
        context_card: dict,
        variant_num: int
    ) -> AdVariant:
        """Rewrite an ad using xai_sdk tool calling for coherent text+image generation."""
        prompt = self._ad_rewrite_prompt(ad, context_card, variant_num)
        temperature = 0.5 + (variant_num * 0.2)
        
        system_msg = system("""You are an expert at rewriting content to match specific writing styles and creating compelling ad creatives.

When you rewrite an ad, you MUST use the generate_ad_image tool to create a visual that complements your copy.
Think holistically - the text and image should work together as a unified creative.""")
        
        ad_copy = ""
        image_url = None
        image_prompt_used = ""
        
        chat = self.client.chat.create(
            model=self.model,
            messages=[system_msg, user(prompt)],
            tools=[self.image_tool],
            tool_choice="auto",
            temperature=temperature,
        )
        
        max_iterations = 3
        for iteration in range(max_iterations):
            try:
                response = chat.sample()
                
                if response.content:
                    content = response.content.strip()
                    content = content.strip('"').strip("'")
                    if content.startswith("```"):
                        lines = content.split("\n")
                        content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                    if content:
                        ad_copy = content.strip()
                
                tool_calls = response.tool_calls
                
                if tool_calls:
                    chat.append(response)
                    
                    for tc in tool_calls:
                        if tc.function.name == "generate_ad_image":
                            args = json.loads(tc.function.arguments)
                            image_prompt_used = args.get("image_prompt", "")
                            tool_ad_copy = args.get("ad_copy", "")
                            
                            if tool_ad_copy:
                                ad_copy = tool_ad_copy
                            
                            print(f"    [Variant {variant_num}] Generating image...")
                            image_url = self._generate_ad_image(image_prompt_used)
                            
                            result_content = json.dumps({
                                "success": image_url is not None,
                                "image_url": image_url,
                                "message": "Image generated successfully" if image_url else "Image generation failed"
                            })
                            chat.append(tool_result(result_content))
                    continue
                else:
                    if response.finish_reason in ["STOP", "stop", "FINISH_REASON_STOP"]:
                        break
                    break
                    
            except Exception as e:
                print(f"Error in ad variant {variant_num}: {e}")
                break
        
        if not ad_copy:
            ad_copy = ad
            print(f"    [Variant {variant_num}] Using original ad as fallback")
        
        return AdVariant(
            content=ad_copy,
            image_uri=image_url,
            image_prompt=image_prompt_used
        )

    def remix_ads(
        self,
        context_card: Union[dict, 'ContextCard'],
        ads: Optional[List[str]] = None
    ) -> RemixedAdsResult:
        """
        Main method to remix ads.
        
        Args:
            context_card: User context card (dict or ContextCard)
            ads: List of candidate ads (uses DEFAULT_ADS if not provided)
            
        Returns:
            RemixedAdsResult with selected ad and 3 variants
        """
        # Convert ContextCard to dict if needed
        if hasattr(context_card, 'to_dict'):
            context_card = context_card.to_dict()
        
        # Use default ads if none provided
        if ads is None:
            ads = DEFAULT_ADS
        
        if not ads:
            raise ValueError("At least one ad is required")
        
        if len(ads) > 5:
            ads = ads[:5]
        
        user_id = context_card.get("user_id") or context_card.get("username", "unknown")
        
        # Step 1: Select the best ad
        print("  Selecting best ad...")
        selection = self._select_best_ad(ads, context_card)
        selected_ad = selection.get("selected_ad_text", ads[0])
        print(f"    Selected: {selected_ad[:60]}...")
        
        # Step 2: Rewrite the selected ad into 3 parallel variants
        print("  Generating 3 ad variants with images...")
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(self._rewrite_ad_variant, selected_ad, context_card, i+1)
                for i in range(3)
            ]
            rewritten_ads = [f.result() for f in futures]
        
        return RemixedAdsResult(
            user_id=user_id,
            selected_ad=selected_ad,
            selection_reasoning=selection.get("reasoning", ""),
            rewritten_ads=rewritten_ads
        )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        context_file = sys.argv[1]
        print(f"Loading context card from {context_file}...")
        with open(context_file, 'r', encoding='utf-8') as f:
            context_card = json.load(f)
        
        print("Remixing ads...")
        agent = AdRemixerAgent()
        result = agent.remix_ads(context_card)
        
        print(f"\n✓ Remixed ads for user: {result.user_id}")
        print(f"  Selected ad: {result.selected_ad[:60]}...")
        print(f"  Variants: {len(result.rewritten_ads)}")
        
        for i, variant in enumerate(result.rewritten_ads, 1):
            print(f"\n  Variant {i}: {variant.content[:80]}...")
            if variant.image_uri:
                print(f"    Image: {variant.image_uri[:60]}...")
        
        # Save to JSON
        output_file = "remixed_ads_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved to: {output_file}")
    else:
        print("Usage: python ad_remixer.py <context_card.json>")

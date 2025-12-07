"""
Ad Remixer Agent
Takes user context card and list of ads, picks the best ad, and rewrites it 
into 3 parallel versions matching the user's style from top_25_reranked_posts.

Uses tool calling to coherently generate ad text and images together.
"""

import os
import json
import asyncio
from typing import Optional, List
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# Tool definition for image generation
IMAGE_GENERATION_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_ad_image",
        "description": "Generate a compelling visual image for the ad. Call this AFTER you've written the ad copy to create a coherent image that complements the text.",
        "parameters": {
            "type": "object",
            "properties": {
                "image_prompt": {
                    "type": "string",
                    "description": "A detailed prompt describing the image to generate. Include style, mood, colors, composition, and key visual elements that align with the ad copy. Be specific about what should be shown."
                },
                "ad_copy": {
                    "type": "string",
                    "description": "The final ad copy text that this image should complement."
                }
            },
            "required": ["image_prompt", "ad_copy"]
        }
    }
}


class AdRemixerAgent:
    """Agent that remixes ads to match user's style using coherent text+image generation."""
    
    BASE_URL = "https://api.x.ai/v1/chat/completions"
    IMAGE_URL = "https://api.x.ai/v1/images/generations"
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "grok-4-1-fast-non-reasoning"
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
        """Prompt for rewriting an ad in user's style with coherent image generation."""
        style_ref = self._build_style_reference(context_card)
        
        # Different creative directions for each variant
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

    async def _generate_ad_image(
        self, 
        client: httpx.AsyncClient, 
        image_prompt: str
    ) -> Optional[str]:
        """Generate an image using xAI image generation API.
        
        Args:
            client: HTTP client
            image_prompt: Detailed prompt for the image
            
        Returns:
            Image URL if successful, None otherwise
        """
        try:
            payload = {
                "model": "grok-imagine-v0p9",
                "prompt": image_prompt,
                "response_format": "url"
            }
            
            r = await client.post(self.IMAGE_URL, json=payload, headers=self.headers)
            r.raise_for_status()
            response_data = r.json()
            
            # Extract URL from response
            if "data" in response_data and len(response_data["data"]) > 0:
                return response_data["data"][0].get("url")
            
            print(f"Warning: Could not extract image URL from response: {response_data}")
            return None
                
        except Exception as e:
            print(f"Error generating image: {e}")
            return None

    async def _rewrite_ad_variant(
        self,
        client: httpx.AsyncClient,
        ad: str,
        context_card: dict,
        variant_num: int
    ) -> dict:
        """Rewrite an ad using tool calling for coherent text+image generation."""
        prompt = self._ad_rewrite_prompt(ad, context_card, variant_num)
        
        # Different temperatures for diversity
        temperature = 0.5 + (variant_num * 0.2)
        
        messages = [
            {
                "role": "system",
                "content": """You are an expert at rewriting content to match specific writing styles and creating compelling ad creatives.

When you rewrite an ad, you MUST use the generate_ad_image tool to create a visual that complements your copy.
Think holistically - the text and image should work together as a unified creative."""
            },
            {"role": "user", "content": prompt}
        ]
        
        ad_copy = ""
        image_url = None
        image_prompt_used = ""
        
        # Agentic tool calling loop
        max_iterations = 3
        for iteration in range(max_iterations):
            payload = {
                "model": self.model,
                "messages": messages,
                "tools": [IMAGE_GENERATION_TOOL],
                "tool_choice": "auto",
                "temperature": temperature,
                "max_tokens": 1000
            }
            
            try:
                r = await client.post(self.BASE_URL, json=payload, headers=self.headers)
                r.raise_for_status()
                response_data = r.json()
                choice = response_data["choices"][0]
                message = choice["message"]
                finish_reason = choice.get("finish_reason", "")
                
                # Check if there's text content (the ad copy)
                if message.get("content"):
                    content = message["content"].strip()
                    # Clean up if wrapped in quotes or code blocks
                    content = content.strip('"').strip("'")
                    if content.startswith("```"):
                        lines = content.split("\n")
                        content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                    if content:
                        ad_copy = content.strip()
                
                # Check for tool calls
                tool_calls = message.get("tool_calls", [])
                
                if tool_calls:
                    # Add assistant message with tool calls to conversation
                    messages.append(message)
                    
                    for tool_call in tool_calls:
                        if tool_call["function"]["name"] == "generate_ad_image":
                            # Parse arguments
                            args = json.loads(tool_call["function"]["arguments"])
                            image_prompt_used = args.get("image_prompt", "")
                            tool_ad_copy = args.get("ad_copy", "")
                            
                            # If we got ad_copy from tool call, use it (it's the final version)
                            if tool_ad_copy:
                                ad_copy = tool_ad_copy
                            
                            print(f"  [Variant {variant_num}] Generating image with prompt: {image_prompt_used[:100]}...")
                            
                            # Generate the image
                            image_url = await self._generate_ad_image(client, image_prompt_used)
                            
                            # Add tool result to messages
                            tool_result = {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": json.dumps({
                                    "success": image_url is not None,
                                    "image_url": image_url,
                                    "message": "Image generated successfully" if image_url else "Image generation failed"
                                })
                            }
                            messages.append(tool_result)
                
                # If no tool calls and we have content, or finish_reason is "stop", we're done
                if finish_reason == "stop" and not tool_calls:
                    break
                    
                # If we've processed tool calls, continue the loop to let model respond
                if not tool_calls:
                    break
                    
            except Exception as e:
                print(f"Error in ad variant {variant_num} iteration {iteration}: {e}")
                break
        
        # Fallback if no ad copy was generated
        if not ad_copy:
            ad_copy = ad
            print(f"  [Variant {variant_num}] Warning: Using original ad as fallback")
        
        return {
            "content": ad_copy,
            "image_uri": image_url,
            "image_prompt": image_prompt_used
        }

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
        
        async with httpx.AsyncClient(timeout=120.0) as client:
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
            "rewritten_ads": rewritten_ads,
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
        context_card_file = "../x_auth/user_data_xhardiksr_1997090614605934592_context_card.json"
    
    print(f"Loading context card from {context_card_file}...")
    with open(context_card_file, 'r', encoding='utf-8') as f:
        context_card = json.load(f)
    
    # Example ads (in real usage, these would come from another system)
    example_ads = [
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
    
    print("\nRemixing ads with coherent text + image generation...")
    agent = AdRemixerAgent()
    result = agent.remix_ads(context_card, example_ads)
    
    print("\n" + "="*60)
    print("AD REMIX RESULTS (Coherent Text + Image)")
    print("="*60)
    print(f"\nUser ID: {result['user_id']}")
    print(f"\nRewritten Ads ({len(result['rewritten_ads'])} variants):")
    print("-" * 60)
    for i, ad_data in enumerate(result['rewritten_ads'], 1):
        print(f"\nVariant {i}:")
        print(f"  Ad Copy: \"{ad_data.get('content', 'N/A')}\"")
        print(f"  Image Prompt: \"{ad_data.get('image_prompt', 'N/A')[:100]}...\"" if ad_data.get('image_prompt') else "  Image Prompt: N/A")
        print(f"  Image URL: {ad_data.get('image_uri') or 'None'}")
    
    # Save to JSON
    output_file = "remixed_ads_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n\nResults saved to: {output_file}")

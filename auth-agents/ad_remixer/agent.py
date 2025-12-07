"""
Ad Remixer Agent
Takes user context card and list of ads, picks the best ad, and rewrites it 
into 3 parallel versions matching the user's style from top_25_reranked_posts.

Uses tool calling to coherently generate ad text and images together.
Supports image editing by using the original ad image as a reference for enhancements.
"""

import os
import json
import asyncio
import base64
from typing import Optional, List, Dict, Any

import httpx
from dotenv import load_dotenv

from .supabase_client import fetch_ads, fetch_persona
from .scoring import rank_ads

# Load environment variables from .env file
load_dotenv()


# Tool definition for image generation/editing
IMAGE_GENERATION_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_ad_image",
        "description": "Generate or enhance a compelling visual image for the ad. Call this AFTER you've written the ad copy. If an original image is available, describe how to improve it while preserving its core elements.",
        "parameters": {
            "type": "object",
            "properties": {
                "image_prompt": {
                    "type": "string",
                    "description": "A detailed prompt describing the image to generate or how to enhance the original. Include style, mood, colors, composition, and key visual elements. If editing, specify what to keep, modify, or enhance from the original."
                },
                "ad_copy": {
                    "type": "string",
                    "description": "The final ad copy text that this image should complement."
                },
                "enhancement_notes": {
                    "type": "string",
                    "description": "Specific notes on how this image improves upon or differs from the original ad image (if original exists)."
                }
            },
            "required": ["image_prompt", "ad_copy"]
        }
    }
}

# Tool definition for CTR scoring of image variants
CTR_SCORING_TOOL = {
    "type": "function",
    "function": {
        "name": "score_image_ctr",
        "description": "Score the predicted CTR (Click-Through Rate) for different image variants. Use this to compare the original image against enhanced versions and determine which performs best.",
        "parameters": {
            "type": "object",
            "properties": {
                "original_image_url": {
                    "type": "string",
                    "description": "URL of the original ad image"
                },
                "enhanced_image_url": {
                    "type": "string",
                    "description": "URL of the enhanced/generated image"
                },
                "ad_copy": {
                    "type": "string",
                    "description": "The ad copy text to evaluate with each image"
                },
                "user_context": {
                    "type": "string",
                    "description": "Brief description of the target user's interests and style"
                }
            },
            "required": ["ad_copy", "user_context"]
        }
    }
}


class AdRemixerAgent:
    """Agent that remixes ads to match user's style using coherent text+image generation.
    
    Supports:
    - Image editing using original ad image as reference
    - CTR scoring to compare original vs enhanced images
    - Multimodal image analysis for intelligent enhancements
    """
    
    BASE_URL = "https://api.x.ai/v1/chat/completions"
    IMAGE_URL = "https://api.x.ai/v1/images/generations"
    VISION_MODEL = "grok-imagine-v0p9"  # Vision model for image analysis
    IMAGE_MODEL = "grok-imagine-v0p9"  # Image generation model with multimodal support
    
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

    def _persona_from_context(self, context_card: dict) -> Dict[str, Any]:
        """
        Build a minimal persona dict from the context card as fallback.
        """
        return {
            "persona": context_card.get("user_persona_tone") or context_card.get("company_persona") or "",
            "categories": context_card.get("categories") or [],
            "strictly_against": context_card.get("strictly_against") or [],
        }

    def _compose_ad_text(self, ad: Dict[str, Any]) -> str:
        """
        Build a readable ad string from structured fields for scoring/remixing.
        """
        title = ad.get("title") or ""
        desc = ad.get("description") or ""
        tagline = ad.get("tagline") or ""
        parts = [p for p in [title, desc, tagline] if p]
        return " — ".join(parts) if parts else ""

    def rank_supabase_ads(
        self,
        user_id: str,
        context_card: dict,
        limit: int = 50,
        log_ranking: bool = False,
    ) -> Dict[str, Any]:
        """
        Fetch ads + persona from Supabase, score, and return ranked list.

        Requires env: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (preferred) or SUPABASE_ANON_KEY.
        Schema expectations:
        - ad_campaigns: id,title,description,company,tagline,image_url,company_persona,strictly_against,categories,created_at
        - personas: user_id, persona, strictly_against, categories (optional)
        """
        persona = fetch_persona(user_id) or self._persona_from_context(context_card)
        ads = fetch_ads(limit=limit)
        ranked_ads = rank_ads(ads, persona)

        if log_ranking:
            print("\n[ad_remixer] Ranked ads (top 10):")
            for idx, ad in enumerate(ranked_ads[:10], start=1):
                title = ad.get("title") or ad.get("description") or "(no title)"
                score = ad["scores"]["total"]
                print(f"  {idx:02d}. score={score:5.1f} | {title[:120]}")

        return {"persona": persona, "ads": ranked_ads}

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

    async def _analyze_original_image(
        self,
        client: httpx.AsyncClient,
        image_url: str,
        ad_copy: str,
        context_card: dict
    ) -> Dict[str, Any]:
        """Analyze the original ad image using vision model to guide enhancements.
        
        Returns:
            Dict with image analysis including:
            - description: What the image shows
            - strengths: Visual elements that work well
            - improvement_suggestions: How to enhance for the target user
            - key_elements: Elements to preserve in any edit
        """
        style_ref = self._build_style_reference(context_card)
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert at analyzing ad creatives and suggesting improvements. Analyze images with a focus on what would resonate with the target user."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url, "detail": "high"}
                    },
                    {
                        "type": "text",
                        "text": f"""Analyze this ad image for the following ad copy:
"{ad_copy}"

Target user context:
{style_ref}

Provide a JSON response with:
{{
    "description": "Brief description of what the image shows",
    "strengths": ["list of visual elements that work well"],
    "improvement_suggestions": ["specific suggestions to make it more appealing to this user"],
    "key_elements": ["core elements that should be preserved in any edit"],
    "style_notes": "overall style and mood of the image"
}}"""
                    }
                ]
            }
        ]
        
        payload = {
            "model": self.VISION_MODEL,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 800
        }
        
        try:
            r = await client.post(self.BASE_URL, json=payload, headers=self.headers)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"].strip()
            
            # Extract JSON from response
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            return json.loads(content)
        except Exception as e:
            print(f"Warning: Image analysis failed: {e}")
            return {
                "description": "Original ad image",
                "strengths": [],
                "improvement_suggestions": [],
                "key_elements": [],
                "style_notes": "unknown"
            }

    async def _score_image_ctr(
        self,
        client: httpx.AsyncClient,
        images: List[Dict[str, Any]],
        ad_copy: str,
        context_card: dict
    ) -> List[Dict[str, Any]]:
        """Score multiple image variants for predicted CTR.
        
        Args:
            images: List of dicts with 'url', 'type' ('original' or 'enhanced'), 'variant_num'
            ad_copy: The ad copy text
            context_card: User context for personalization
            
        Returns:
            List of images with added 'ctr_score' and 'ctr_reasoning' fields, sorted by score
        """
        if not images:
            return []
        
        style_ref = self._build_style_reference(context_card)
        
        # Build image content for multimodal analysis
        image_contents = []
        for i, img in enumerate(images):
            if img.get("url"):
                image_contents.append({
                    "type": "image_url",
                    "image_url": {"url": img["url"], "detail": "high"}
                })
                image_contents.append({
                    "type": "text",
                    "text": f"[Image {i+1}: {img.get('type', 'unknown')} - Variant {img.get('variant_num', 'N/A')}]"
                })
        
        if not image_contents:
            return images
        
        image_contents.append({
            "type": "text",
            "text": f"""Score each image above for predicted Click-Through Rate (CTR) when paired with this ad copy:
"{ad_copy}"

Target user context:
{style_ref}

For each image, consider:
1. Visual appeal and attention-grabbing quality
2. Relevance to the ad message
3. Alignment with user's interests and style preferences
4. Professional quality and trustworthiness
5. Emotional resonance with the target audience

Return JSON array with scores (0-100) for each image:
[
    {{"image_index": 1, "ctr_score": 85, "reasoning": "Brief explanation"}},
    ...
]"""
        })
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert at predicting ad performance and CTR based on visual and textual elements."
            },
            {
                "role": "user",
                "content": image_contents
            }
        ]
        
        payload = {
            "model": self.VISION_MODEL,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        try:
            r = await client.post(self.BASE_URL, json=payload, headers=self.headers)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"].strip()
            
            # Extract JSON from response
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            scores = json.loads(content)
            
            # Add scores to images
            for score_data in scores:
                idx = score_data.get("image_index", 0) - 1
                if 0 <= idx < len(images):
                    images[idx]["ctr_score"] = score_data.get("ctr_score", 50)
                    images[idx]["ctr_reasoning"] = score_data.get("reasoning", "")
            
            # Sort by CTR score descending
            images.sort(key=lambda x: x.get("ctr_score", 0), reverse=True)
            return images
            
        except Exception as e:
            print(f"Warning: CTR scoring failed: {e}")
            # Return images with default scores
            for img in images:
                img["ctr_score"] = 50
                img["ctr_reasoning"] = "Scoring unavailable"
            return images

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

    def _ad_rewrite_prompt(
        self, 
        ad: str, 
        context_card: dict, 
        variant_num: int,
        original_image_url: Optional[str] = None,
        image_analysis: Optional[Dict[str, Any]] = None
    ) -> str:
        """Prompt for rewriting an ad in user's style with coherent image generation.
        
        Args:
            ad: Original ad text
            context_card: User context card
            variant_num: Which variant (1, 2, or 3)
            original_image_url: Optional URL of the original ad image
            image_analysis: Optional analysis of the original image
        """
        style_ref = self._build_style_reference(context_card)
        
        # Different creative directions for each variant
        variant_instructions = {
            1: "Focus on their most casual, conversational style. Use their typical slang and informal tone. Image should feel authentic and relatable.",
            2: "Match their authentic voice but emphasize the core benefit more directly. Image should highlight the key value proposition.",
            3: "Channel their personality but take a slightly different angle or hook on the message. Image should be eye-catching and memorable."
        }
        
        variation = variant_instructions.get(variant_num, variant_instructions[1])
        
        # Build image context section if original image exists
        image_context = ""
        if original_image_url and image_analysis:
            strengths = image_analysis.get("strengths", [])
            improvements = image_analysis.get("improvement_suggestions", [])
            key_elements = image_analysis.get("key_elements", [])
            
            image_context = f"""

ORIGINAL AD IMAGE ANALYSIS:
- Description: {image_analysis.get('description', 'N/A')}
- Strengths to preserve: {', '.join(strengths) if strengths else 'N/A'}
- Key elements to keep: {', '.join(key_elements) if key_elements else 'N/A'}
- Suggested improvements: {', '.join(improvements) if improvements else 'N/A'}

When generating the enhanced image:
- Build upon the original image's strengths
- Preserve key brand/product elements
- Apply the suggested improvements to better resonate with this user
- The enhanced image should feel like an evolution, not a complete departure"""
        elif original_image_url:
            image_context = f"""

ORIGINAL AD IMAGE: {original_image_url}
When generating the enhanced image, consider how to improve upon the original while preserving its core message and brand elements."""
        
        return f"""{style_ref}

ORIGINAL AD:
"{ad}"{image_context}

Your task:
1. Rewrite this ad to match the user's style. {variation}
   Make it sound like THEY wrote it based on the examples above.

2. After writing the ad copy, use the generate_ad_image tool to create a visual that perfectly complements your ad copy.
   - The image should reinforce the message
   - Match the tone and style of the copy
   - Be visually compelling for social media
   - If an original image exists, enhance it rather than creating something completely different

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
        image_prompt: str,
        source_image_url: Optional[str] = None,
        image_analysis: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Generate or enhance an image using xAI image generation API.
        
        Args:
            client: HTTP client
            image_prompt: Detailed prompt for the image
            source_image_url: Optional URL of original image to use as reference
            image_analysis: Optional analysis of the original image for guided enhancement
            
        Returns:
            Image URL if successful, None otherwise
        """
        try:
            # Build enhanced prompt incorporating original image context
            final_prompt = image_prompt
            
            if image_analysis:
                key_elements = image_analysis.get("key_elements", [])
                style_notes = image_analysis.get("style_notes", "")
                
                if key_elements or style_notes:
                    enhancement_context = []
                    if key_elements:
                        enhancement_context.append(f"Preserve these key elements: {', '.join(key_elements)}")
                    if style_notes:
                        enhancement_context.append(f"Original style: {style_notes}")
                    
                    final_prompt = f"{image_prompt}\n\nReference context: {' '.join(enhancement_context)}"
            
            payload = {
                "model": self.IMAGE_MODEL,
                "prompt": final_prompt,
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
        variant_num: int,
        original_image_url: Optional[str] = None,
        image_analysis: Optional[Dict[str, Any]] = None
    ) -> dict:
        """Rewrite an ad using tool calling for coherent text+image generation.
        
        Args:
            client: HTTP client
            ad: Original ad text
            context_card: User context card
            variant_num: Which variant (1, 2, or 3)
            original_image_url: Optional URL of the original ad image for reference
            image_analysis: Optional analysis of the original image
            
        Returns:
            Dict with content, image_uri, image_prompt, and CTR scoring results
        """
        prompt = self._ad_rewrite_prompt(
            ad, context_card, variant_num, 
            original_image_url, image_analysis
        )
        
        # Different temperatures for diversity
        temperature = 0.5 + (variant_num * 0.2)
        
        messages = [
            {
                "role": "system",
                "content": """You are an expert at rewriting content to match specific writing styles and creating compelling ad creatives.

When you rewrite an ad, you MUST use the generate_ad_image tool to create a visual that complements your copy.
Think holistically - the text and image should work together as a unified creative.
If an original image exists, focus on enhancing it rather than creating something completely different."""
            },
            {"role": "user", "content": prompt}
        ]
        
        ad_copy = ""
        enhanced_image_url = None
        image_prompt_used = ""
        enhancement_notes = ""
        
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
                            enhancement_notes = args.get("enhancement_notes", "")
                            
                            # If we got ad_copy from tool call, use it (it's the final version)
                            if tool_ad_copy:
                                ad_copy = tool_ad_copy
                            
                            print(f"  [Variant {variant_num}] Generating enhanced image...")
                            
                            # Generate the enhanced image with original image context
                            enhanced_image_url = await self._generate_ad_image(
                                client, 
                                image_prompt_used,
                                source_image_url=original_image_url,
                                image_analysis=image_analysis
                            )
                            
                            # Add tool result to messages
                            tool_result = {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": json.dumps({
                                    "success": enhanced_image_url is not None,
                                    "image_url": enhanced_image_url,
                                    "message": "Enhanced image generated successfully" if enhanced_image_url else "Image generation failed"
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
        
        # Perform CTR scoring to compare original vs enhanced images
        best_image_url = enhanced_image_url
        ctr_comparison = None
        
        if original_image_url and enhanced_image_url and ad_copy:
            print(f"  [Variant {variant_num}] Scoring CTR for original vs enhanced images...")
            
            images_to_score = [
                {"url": original_image_url, "type": "original", "variant_num": variant_num},
                {"url": enhanced_image_url, "type": "enhanced", "variant_num": variant_num}
            ]
            
            scored_images = await self._score_image_ctr(
                client, images_to_score, ad_copy, context_card
            )
            
            if scored_images:
                # Use the highest scoring image
                best_image = scored_images[0]
                best_image_url = best_image["url"]
                
                ctr_comparison = {
                    "winner": best_image["type"],
                    "winner_score": best_image.get("ctr_score", 0),
                    "winner_reasoning": best_image.get("ctr_reasoning", ""),
                    "all_scores": [
                        {
                            "type": img["type"],
                            "score": img.get("ctr_score", 0),
                            "reasoning": img.get("ctr_reasoning", "")
                        }
                        for img in scored_images
                    ]
                }
                
                print(f"  [Variant {variant_num}] CTR Winner: {best_image['type']} (score: {best_image.get('ctr_score', 0)})")
        
        return {
            "content": ad_copy,
            "image_uri": best_image_url,  # Best performing image
            "enhanced_image_uri": enhanced_image_url,  # Always include enhanced version
            "original_image_uri": original_image_url,  # Include original for reference
            "image_prompt": image_prompt_used,
            "enhancement_notes": enhancement_notes,
            "ctr_comparison": ctr_comparison
        }

    async def remix_ads_async(
        self,
        context_card: dict,
        ads: List[str],
        original_image_url: Optional[str] = None
    ) -> dict:
        """Main async method to remix ads.
        
        Args:
            context_card: User context card with style preferences
            ads: List of ad texts to choose from
            original_image_url: Optional URL of the original ad image for enhancement
            
        Returns:
            Dict with user_id, selected_ad, rewritten_ads (with CTR-optimized images)
        """
        if not ads:
            raise ValueError("At least one ad is required")
        
        if len(ads) > 5:
            ads = ads[:5]  # Limit to 5 ads
        
        # Extract user_id (prefer user_id, fallback to username)
        user_id = context_card.get("user_id") or context_card.get("username", "unknown")
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            # Step 1: Select the best ad
            selection = await self._select_best_ad(client, ads, context_card)
            selected_ad = selection.get("selected_ad_text", ads[0])
            
            # Step 2: Analyze original image if available
            image_analysis = None
            if original_image_url:
                print(f"  Analyzing original ad image...")
                image_analysis = await self._analyze_original_image(
                    client, original_image_url, selected_ad, context_card
                )
                print(f"  Image analysis complete: {image_analysis.get('description', 'N/A')[:80]}...")
            
            # Step 3: Rewrite the selected ad into 3 parallel variants (multi-threaded async calls)
            # Each variant will generate an enhanced image and compare CTR against original
            rewritten_ads = await asyncio.gather(*[
                self._rewrite_ad_variant(
                    client, selected_ad, context_card, i+1,
                    original_image_url=original_image_url,
                    image_analysis=image_analysis
                )
                for i in range(3)
            ])
                
        return {
            "user_id": user_id,
            "selected_ad": selected_ad,
            "selection_reasoning": selection.get("reasoning", ""),
            "original_image_url": original_image_url,
            "image_analysis": image_analysis,
            "rewritten_ads": rewritten_ads,
        }

    async def remix_best_supabase_ad(
        self,
        context_card: dict,
        limit: int = 50,
        log_ranking: bool = True,
    ) -> dict:
        """
        Convenience: fetch + score ads from Supabase, pick the top ad, then remix it.
        
        Uses the original ad's image as a reference for enhancement and performs
        CTR scoring to choose the best image (original vs enhanced) for each variant.

        Returns:
        {
          "user_id": ...,
          "persona": {...},
          "top_ad": {..., "scores": {...}},
          "original_image_url": str or None,
          "image_analysis": {...} or None,
          "remixed_ads": [...]  # 3 variants with CTR-optimized images
        }
        """
        user_id = context_card.get("user_id") or context_card.get("username", "unknown")
        ranked = self.rank_supabase_ads(
            user_id=user_id, context_card=context_card, limit=limit, log_ranking=log_ranking
        )
        if not ranked["ads"]:
            raise ValueError("No ads available in Supabase to remix")

        top_ad = ranked["ads"][0]
        ad_text = self._compose_ad_text(top_ad)
        if not ad_text:
            raise ValueError("Top ad is missing text content")

        # Get the original image URL from the top ad
        original_image_url = top_ad.get("image_url")
        if original_image_url:
            print(f"  Using original ad image for enhancement: {original_image_url[:80]}...")
        else:
            print("  No original image found - will generate new images")

        remix_result = await self.remix_ads_async(
            context_card, 
            [ad_text],
            original_image_url=original_image_url
        )
        
        return {
            "user_id": user_id,
            "persona": ranked["persona"],
            "top_ad": top_ad,
            "original_image_url": original_image_url,
            "image_analysis": remix_result.get("image_analysis"),
            "remixed_ads": remix_result["rewritten_ads"],
        }

    def remix_ads(
        self,
        context_card: dict,
        ads: List[str],
        original_image_url: Optional[str] = None
    ) -> dict:
        """Sync wrapper for remix_ads_async."""
        return asyncio.run(self.remix_ads_async(context_card, ads, original_image_url))


if __name__ == "__main__":
    # Example usage: fetch ads from Supabase, rank, and remix the top ad
    import sys

    if len(sys.argv) > 1:
        context_card_file = sys.argv[1]
    else:
        context_card_file = "../x_auth/user_data_xhardiksr_1997090614605934592_context_card.json"

    print(f"Loading context card from {context_card_file}...")
    with open(context_card_file, 'r', encoding='utf-8') as f:
        context_card = json.load(f)

    agent = AdRemixerAgent()

    async def _run():
        print("\nFetching + ranking ads from Supabase, then remixing the top ad...")
        result = await agent.remix_best_supabase_ad(context_card, limit=50, log_ranking=True)

        print("\n" + "="*60)
        print("AD REMIX RESULTS (With CTR-Optimized Image Selection)")
        print("="*60)
        print(f"\nUser ID: {result['user_id']}")
        print(f"Top ad score: {result['top_ad']['scores']['total']}")
        print(f"Top ad title: {result['top_ad'].get('title')}")
        print(f"Top ad description: {result['top_ad'].get('description')}")
        print(f"Original ad image: {result.get('original_image_url') or 'None'}")
        
        # Show image analysis if available
        if result.get('image_analysis'):
            analysis = result['image_analysis']
            print(f"\nOriginal Image Analysis:")
            print(f"  Description: {analysis.get('description', 'N/A')}")
            print(f"  Strengths: {', '.join(analysis.get('strengths', []))[:100] or 'N/A'}")
            print(f"  Key elements: {', '.join(analysis.get('key_elements', []))[:100] or 'N/A'}")

        print(f"\nRewritten Ads ({len(result['remixed_ads'])} variants):")
        print("-" * 60)
        for i, ad_data in enumerate(result['remixed_ads'], 1):
            print(f"\nVariant {i}:")
            print(f"  Ad Copy: \"{ad_data.get('content', 'N/A')[:200]}...\"")
            if ad_data.get('image_prompt'):
                print(f"  Image Prompt: \"{ad_data.get('image_prompt', 'N/A')[:100]}...\"")
            
            # Show CTR comparison results
            ctr = ad_data.get('ctr_comparison')
            if ctr:
                print(f"  CTR Winner: {ctr.get('winner', 'N/A')} (score: {ctr.get('winner_score', 0)})")
                print(f"  CTR Reasoning: {ctr.get('winner_reasoning', 'N/A')[:100]}")
                print(f"  All Scores:")
                for score_data in ctr.get('all_scores', []):
                    print(f"    - {score_data['type']}: {score_data['score']} - {score_data['reasoning'][:60]}...")
            
            print(f"  Selected Image URL: {ad_data.get('image_uri') or 'None'}")
            print(f"  Original Image URL: {ad_data.get('original_image_uri') or 'None'}")
            print(f"  Enhanced Image URL: {ad_data.get('enhanced_image_uri') or 'None'}")

        output_file = "remixed_ads_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {output_file}")

    asyncio.run(_run())

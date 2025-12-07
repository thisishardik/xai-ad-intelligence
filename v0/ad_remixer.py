"""
Ad Remixer Agent
Takes user context card and list of ads, picks the best ad, and rewrites it 
into 3 parallel versions matching the user's style.

Uses xai_sdk with tool calling to coherently generate ad text and images together.
Supports image editing by using the original ad image as a reference for enhancements.
Performs CTR scoring to compare original vs enhanced images.
"""

import json
from typing import Optional, List, Union, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from xai_sdk import Client
from xai_sdk.chat import user, system, tool, tool_result, image

from config import XAI_API_KEY, DEFAULT_MODEL, IMAGE_MODEL, DEFAULT_ADS
from supabase_client import fetch_ads
from scoring import rank_ads

if TYPE_CHECKING:
    from context_agent import ContextCard

# Vision model for image analysis
VISION_MODEL = "grok-imagine-v0p9"


@dataclass
class CTRScore:
    """CTR scoring result for an image."""
    image_type: str  # 'original' or 'enhanced'
    score: float
    reasoning: str
    
    def to_dict(self) -> dict:
        return {
            "type": self.image_type,
            "score": self.score,
            "reasoning": self.reasoning
        }


@dataclass
class CTRComparison:
    """Comparison of CTR scores between original and enhanced images."""
    winner: str
    winner_score: float
    winner_reasoning: str
    all_scores: List[CTRScore] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "winner": self.winner,
            "winner_score": self.winner_score,
            "winner_reasoning": self.winner_reasoning,
            "all_scores": [s.to_dict() for s in self.all_scores]
        }


@dataclass
class AdVariant:
    """A single ad variant with copy and optional image."""
    content: str
    image_uri: Optional[str] = None  # Best performing image (CTR winner)
    enhanced_image_uri: Optional[str] = None  # Always the enhanced version
    original_image_uri: Optional[str] = None  # Reference to original
    image_prompt: Optional[str] = None
    enhancement_notes: Optional[str] = None
    ctr_comparison: Optional[CTRComparison] = None
    
    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "image_uri": self.image_uri,
            "enhanced_image_uri": self.enhanced_image_uri,
            "original_image_uri": self.original_image_uri,
            "image_prompt": self.image_prompt,
            "enhancement_notes": self.enhancement_notes,
            "ctr_comparison": self.ctr_comparison.to_dict() if self.ctr_comparison else None
        }


@dataclass
class ImageAnalysis:
    """Analysis of the original ad image."""
    description: str
    strengths: List[str]
    improvement_suggestions: List[str]
    key_elements: List[str]
    style_notes: str
    
    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "strengths": self.strengths,
            "improvement_suggestions": self.improvement_suggestions,
            "key_elements": self.key_elements,
            "style_notes": self.style_notes
        }


@dataclass 
class RemixedAdsResult:
    """Result of ad remixing."""
    user_id: str
    selected_ad: str
    selection_reasoning: str
    original_image_url: Optional[str] = None
    image_analysis: Optional[ImageAnalysis] = None
    rewritten_ads: List[AdVariant] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "selected_ad": self.selected_ad,
            "selection_reasoning": self.selection_reasoning,
            "original_image_url": self.original_image_url,
            "image_analysis": self.image_analysis.to_dict() if self.image_analysis else None,
            "rewritten_ads": [ad.to_dict() for ad in self.rewritten_ads]
        }


def create_image_generation_tool():
    """Create the image generation/editing tool definition."""
    return tool(
        name="generate_ad_image",
        description="Generate or enhance a compelling visual image for the ad. Call this AFTER you've written the ad copy. If an original image is available, describe how to improve it while preserving its core elements.",
        parameters={
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
    )


class AdRemixerAgent:
    """Agent that remixes ads to match user's style using coherent text+image generation.
    
    Supports:
    - Image editing using original ad image as reference
    - CTR scoring to compare original vs enhanced images
    - Multimodal image analysis for intelligent enhancements
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = None,
        image_model: str = None,
        vision_model: str = None
    ):
        self.api_key = api_key or XAI_API_KEY
        if not self.api_key:
            raise ValueError("XAI_API_KEY required")
        self.model = model or DEFAULT_MODEL
        self.image_model = image_model or IMAGE_MODEL
        self.vision_model = vision_model or VISION_MODEL
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

    def _analyze_original_image(
        self,
        image_url: str,
        ad_copy: str,
        context_card: dict
    ) -> Optional[ImageAnalysis]:
        """Analyze the original ad image using vision model to guide enhancements.
        
        Returns:
            ImageAnalysis with description, strengths, improvements, key elements
        """
        style_ref = self._build_style_reference(context_card)
        
        chat = self.client.chat.create(model=self.vision_model)
        chat.append(system("You are an expert at analyzing ad creatives and suggesting improvements. Analyze images with a focus on what would resonate with the target user."))
        
        chat.append(
            user(
                f"""Analyze this ad image for the following ad copy:
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
}}""",
                image(image_url)
            )
        )
        
        try:
            response = chat.sample()
            content = response.content.strip()
            
            # Extract JSON from response
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            data = json.loads(content)
            return ImageAnalysis(
                description=data.get("description", "Original ad image"),
                strengths=data.get("strengths", []),
                improvement_suggestions=data.get("improvement_suggestions", []),
                key_elements=data.get("key_elements", []),
                style_notes=data.get("style_notes", "unknown")
            )
        except Exception as e:
            print(f"Warning: Image analysis failed: {e}")
            return None

    def _score_image_ctr(
        self,
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
        
        # Filter out images without URLs
        valid_images = [img for img in images if img.get("url")]
        if not valid_images:
            return images
        
        style_ref = self._build_style_reference(context_card)
        
        chat = self.client.chat.create(model=self.vision_model)
        chat.append(system("You are an expert at predicting ad performance and CTR based on visual and textual elements."))
        
        # Build the user message with images
        image_refs = []
        image_labels = []
        for i, img in enumerate(valid_images):
            image_refs.append(image(img["url"]))
            image_labels.append(f"[Image {i+1}: {img.get('type', 'unknown')} - Variant {img.get('variant_num', 'N/A')}]")
        
        prompt_text = f"""Score each image above for predicted Click-Through Rate (CTR) when paired with this ad copy:
"{ad_copy}"

Image labels: {', '.join(image_labels)}

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
        
        # Add all images followed by the text prompt
        chat.append(user(prompt_text, *image_refs))
        
        try:
            response = chat.sample()
            content = response.content.strip()
            
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
                if 0 <= idx < len(valid_images):
                    valid_images[idx]["ctr_score"] = score_data.get("ctr_score", 50)
                    valid_images[idx]["ctr_reasoning"] = score_data.get("reasoning", "")
            
            # Sort by CTR score descending
            valid_images.sort(key=lambda x: x.get("ctr_score", 0), reverse=True)
            return valid_images
            
        except Exception as e:
            print(f"Warning: CTR scoring failed: {e}")
            # Return images with default scores
            for img in valid_images:
                img["ctr_score"] = 50
                img["ctr_reasoning"] = "Scoring unavailable"
            return valid_images

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
        image_analysis: Optional[ImageAnalysis] = None
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
        
        variant_instructions = {
            1: "Focus on their most casual, conversational style. Use their typical slang and informal tone. Image should feel authentic and relatable.",
            2: "Match their authentic voice but emphasize the core benefit more directly. Image should highlight the key value proposition.",
            3: "Channel their personality but take a slightly different angle or hook on the message. Image should be eye-catching and memorable."
        }
        
        variation = variant_instructions.get(variant_num, variant_instructions[1])
        
        # Build image context section if original image exists
        image_context = ""
        if original_image_url and image_analysis:
            strengths = image_analysis.strengths
            improvements = image_analysis.improvement_suggestions
            key_elements = image_analysis.key_elements
            
            image_context = f"""

ORIGINAL AD IMAGE ANALYSIS:
- Description: {image_analysis.description}
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

    def _compose_ad_text(self, ad: Dict[str, Any]) -> str:
        """Compose a readable ad text from structured fields."""
        if isinstance(ad, str):
            return ad
        parts = [ad.get("title") or "", ad.get("description") or "", ad.get("tagline") or ""]
        parts = [p for p in parts if p]
        return " — ".join(parts) if parts else ""

    def _generate_ad_image(
        self, 
        image_prompt: str,
        image_analysis: Optional[ImageAnalysis] = None
    ) -> Optional[str]:
        """Generate or enhance an image using xai_sdk image generation.
        
        Args:
            image_prompt: Detailed prompt for the image
            image_analysis: Optional analysis of the original image for guided enhancement
            
        Returns:
            Image URL if successful, None otherwise
        """
        try:
            # Build enhanced prompt incorporating original image context
            final_prompt = image_prompt
            
            if image_analysis:
                key_elements = image_analysis.key_elements
                style_notes = image_analysis.style_notes
                
                if key_elements or style_notes:
                    enhancement_context = []
                    if key_elements:
                        enhancement_context.append(f"Preserve these key elements: {', '.join(key_elements)}")
                    if style_notes:
                        enhancement_context.append(f"Original style: {style_notes}")
                    
                    final_prompt = f"{image_prompt}\n\nReference context: {' '.join(enhancement_context)}"
            
            response = self.client.image.sample(
                model=self.image_model,
                prompt=final_prompt,
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
        variant_num: int,
        original_image_url: Optional[str] = None,
        image_analysis: Optional[ImageAnalysis] = None
    ) -> AdVariant:
        """Rewrite an ad using xai_sdk tool calling for coherent text+image generation.
        
        Args:
            ad: Original ad text
            context_card: User context card
            variant_num: Which variant (1, 2, or 3)
            original_image_url: Optional URL of the original ad image for reference
            image_analysis: Optional analysis of the original image
            
        Returns:
            AdVariant with content, images, and CTR scoring results
        """
        prompt = self._ad_rewrite_prompt(
            ad, context_card, variant_num, 
            original_image_url, image_analysis
        )
        temperature = 0.5 + (variant_num * 0.2)
        
        system_msg = system("""You are an expert at rewriting content to match specific writing styles and creating compelling ad creatives.

When you rewrite an ad, you MUST use the generate_ad_image tool to create a visual that complements your copy.
Think holistically - the text and image should work together as a unified creative.
If an original image exists, focus on enhancing it rather than creating something completely different.""")
        
        ad_copy = ""
        enhanced_image_url = None
        image_prompt_used = ""
        enhancement_notes = ""
        
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
                            enhancement_notes = args.get("enhancement_notes", "")
                            
                            if tool_ad_copy:
                                ad_copy = tool_ad_copy
                            
                            print(f"    [Variant {variant_num}] Generating enhanced image...")
                            enhanced_image_url = self._generate_ad_image(
                                image_prompt_used,
                                image_analysis=image_analysis
                            )
                            
                            result_content = json.dumps({
                                "success": enhanced_image_url is not None,
                                "image_url": enhanced_image_url,
                                "message": "Enhanced image generated successfully" if enhanced_image_url else "Image generation failed"
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
        
        # Perform CTR scoring to compare original vs enhanced images
        best_image_url = enhanced_image_url
        ctr_comparison = None
        
        if original_image_url and enhanced_image_url and ad_copy:
            print(f"    [Variant {variant_num}] Scoring CTR for original vs enhanced images...")
            
            images_to_score = [
                {"url": original_image_url, "type": "original", "variant_num": variant_num},
                {"url": enhanced_image_url, "type": "enhanced", "variant_num": variant_num}
            ]
            
            scored_images = self._score_image_ctr(images_to_score, ad_copy, context_card)
            
            if scored_images:
                # Use the highest scoring image
                best_image = scored_images[0]
                best_image_url = best_image["url"]
                
                ctr_scores = [
                    CTRScore(
                        image_type=img["type"],
                        score=img.get("ctr_score", 0),
                        reasoning=img.get("ctr_reasoning", "")
                    )
                    for img in scored_images
                ]
                
                ctr_comparison = CTRComparison(
                    winner=best_image["type"],
                    winner_score=best_image.get("ctr_score", 0),
                    winner_reasoning=best_image.get("ctr_reasoning", ""),
                    all_scores=ctr_scores
                )
                
                print(f"    [Variant {variant_num}] CTR Winner: {best_image['type']} (score: {best_image.get('ctr_score', 0)})")
        
        return AdVariant(
            content=ad_copy,
            image_uri=best_image_url,  # Best performing image (CTR winner)
            enhanced_image_uri=enhanced_image_url,  # Always include enhanced version
            original_image_uri=original_image_url,  # Reference to original
            image_prompt=image_prompt_used,
            enhancement_notes=enhancement_notes,
            ctr_comparison=ctr_comparison
        )

    def remix_ads(
        self,
        context_card: Union[dict, 'ContextCard'],
        ads: Optional[List[Union[str, Dict[str, Any]]]] = None,
        log_ranking: bool = True,
        supabase_limit: int = 50,
        original_image_url: Optional[str] = None,
    ) -> RemixedAdsResult:
        """
        Main method to remix ads.

        Args:
            context_card: User context card (dict or ContextCard)
            ads: List of candidate ads (if None, fetch from Supabase ad_campaigns)
            log_ranking: print ranked ads (top 10) before remixing
            supabase_limit: max ads to fetch from Supabase when ads is None
            original_image_url: Optional URL of original image for enhancement

        Returns:
            RemixedAdsResult with selected ad, 3 variants with CTR-optimized images
        """
        # Convert ContextCard to dict if needed
        if hasattr(context_card, 'to_dict'):
            context_card = context_card.to_dict()

        # Build persona for scoring
        persona = {
            "persona": context_card.get("user_persona_tone", ""),
            "categories": context_card.get("categories") or [],
            "strictly_against": context_card.get("strictly_against") or [],
        }

        # Fetch ads from Supabase if none provided
        if ads is None:
            try:
                ads = fetch_ads(limit=supabase_limit)
                print(f"  Fetched {len(ads)} ads from Supabase.")
            except Exception as e:
                print(f"  Warning: Supabase fetch failed ({e}); falling back to DEFAULT_ADS.")
                ads = []

        if not ads:
            print("  Warning: No ads from Supabase; using DEFAULT_ADS fallback.")
            ads = DEFAULT_ADS

        # Normalize to structured ads
        structured_ads: List[Dict[str, Any]] = []
        for ad in ads:
            if isinstance(ad, str):
                structured_ads.append({"title": ad})
            else:
                structured_ads.append(ad)

        ranked_ads = rank_ads(structured_ads, persona)

        if log_ranking:
            print("\n  Ranked ads (top 10):")
            for idx, ad in enumerate(ranked_ads[:10], start=1):
                score = ad["scores"]["total"]
                text = self._compose_ad_text(ad)
                print(f"    {idx:02d}. score={score:5.1f} | {text[:120]}")

        top_ad = ranked_ads[0]
        selected_ad = self._compose_ad_text(top_ad)
        user_id = context_card.get("user_id") or context_card.get("username", "unknown")

        # Get original image from top ad if not explicitly provided
        if original_image_url is None:
            original_image_url = top_ad.get("image_url")
        
        if original_image_url:
            print(f"  Using original ad image for enhancement: {original_image_url[:80]}...")
        else:
            print("  No original image found - will generate new images")

        print("  Selecting best ad from Supabase scoring...")
        print(f"    Selected: {selected_ad[:80]}...")

        # Step 2: Analyze original image if available
        image_analysis = None
        if original_image_url:
            print("  Analyzing original ad image...")
            image_analysis = self._analyze_original_image(
                original_image_url, selected_ad, context_card
            )
            if image_analysis:
                print(f"    Analysis complete: {image_analysis.description[:80]}...")

        # Step 3: Rewrite the selected ad into 3 parallel variants with CTR optimization
        print("  Generating 3 ad variants with CTR-optimized images...")
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(
                    self._rewrite_ad_variant, 
                    selected_ad, context_card, i+1,
                    original_image_url, image_analysis
                )
                for i in range(3)
            ]
            rewritten_ads = [f.result() for f in futures]

        return RemixedAdsResult(
            user_id=user_id,
            selected_ad=selected_ad,
            selection_reasoning=f"Highest score {top_ad['scores']['total']}",
            original_image_url=original_image_url,
            image_analysis=image_analysis,
            rewritten_ads=rewritten_ads
        )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        context_file = sys.argv[1]
        print(f"Loading context card from {context_file}...")
        with open(context_file, 'r', encoding='utf-8') as f:
            context_card = json.load(f)
        
        print("Remixing ads with CTR-optimized image selection...")
        agent = AdRemixerAgent()
        result = agent.remix_ads(context_card)
        
        print(f"\n" + "="*60)
        print("AD REMIX RESULTS (With CTR-Optimized Image Selection)")
        print("="*60)
        print(f"\n✓ Remixed ads for user: {result.user_id}")
        print(f"  Selected ad: {result.selected_ad[:60]}...")
        print(f"  Original image: {result.original_image_url or 'None'}")
        
        # Show image analysis if available
        if result.image_analysis:
            print(f"\nOriginal Image Analysis:")
            print(f"  Description: {result.image_analysis.description}")
            print(f"  Strengths: {', '.join(result.image_analysis.strengths)[:100] or 'N/A'}")
            print(f"  Key elements: {', '.join(result.image_analysis.key_elements)[:100] or 'N/A'}")
        
        print(f"\nVariants ({len(result.rewritten_ads)}):")
        print("-" * 60)
        
        for i, variant in enumerate(result.rewritten_ads, 1):
            print(f"\n  Variant {i}: {variant.content[:80]}...")
            
            # Show CTR comparison results
            if variant.ctr_comparison:
                ctr = variant.ctr_comparison
                print(f"    CTR Winner: {ctr.winner} (score: {ctr.winner_score})")
                print(f"    CTR Reasoning: {ctr.winner_reasoning[:80]}...")
                print(f"    All Scores:")
                for score in ctr.all_scores:
                    print(f"      - {score.image_type}: {score.score} - {score.reasoning[:50]}...")
            
            print(f"    Selected Image: {variant.image_uri[:60] if variant.image_uri else 'None'}...")
            print(f"    Original Image: {variant.original_image_uri[:60] if variant.original_image_uri else 'None'}...")
            print(f"    Enhanced Image: {variant.enhanced_image_uri[:60] if variant.enhanced_image_uri else 'None'}...")
        
        # Save to JSON
        output_file = "remixed_ads_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved to: {output_file}")
    else:
        print("Usage: python ad_remixer.py <context_card.json>")

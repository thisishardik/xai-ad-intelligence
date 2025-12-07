"""
Context Agent for User Persona Analysis
Analyzes user's posts, timeline, likes, and bookmarks to create a context card.
"""

import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from xai_sdk import Client
from xai_sdk.chat import system, user

# Load environment variables from .env file
load_dotenv()


class RerankedPostInput(BaseModel):
    """Minimal reranked post input from Grok (only ID, rank, and score)."""
    post_id: str = Field(description="The unique ID in format 'source.id' (e.g., 'timeline.123456', 'likes.789012')")
    rank: int = Field(description="Rank position (1-25)", ge=1, le=25)
    relevance_score: float = Field(description="Relevance score (0-1)", ge=0.0, le=1.0)


class RerankedPost(BaseModel):
    """A reranked post with its score and full data."""
    post_id: str = Field(description="The unique ID of the post")
    text: str = Field(description="The text content of the post")
    source: str = Field(description="Source: 'posts', 'timeline', 'likes', or 'bookmarks'")
    rank: int = Field(description="Rank position (1-25)", ge=1, le=25)
    relevance_score: float = Field(description="Relevance score (0-1)", ge=0.0, le=1.0)


class ContextCardInput(BaseModel):
    """Context card input from Grok (minimal data)."""
    username: Optional[str] = Field(default=None, description="The username of the user")
    general_topic: str = Field(description="General topic or theme the user is interested in")
    popular_memes: Optional[str] = Field(
        default=None,
        description="Popular memes or trending content patterns in the latest posts/timeline"
    )
    user_persona_tone: str = Field(
        description="General tone of the user persona (e.g., 'casual and humorous', 'professional and technical', 'thoughtful and reflective')"
    )
    top_25_reranked_posts: List[RerankedPostInput] = Field(
        description="Top 25 posts reranked from all available posts, timeline, likes, and bookmarks. Only provide post_id, rank, and relevance_score.",
        min_length=1,
        max_length=25
    )


class ContextCard(BaseModel):
    """Context card output with full data."""
    username: Optional[str] = Field(default=None, description="The username of the user")
    general_topic: str = Field(description="General topic or theme the user is interested in")
    popular_memes: Optional[str] = Field(
        default=None,
        description="Popular memes or trending content patterns in the latest posts/timeline"
    )
    user_persona_tone: str = Field(
        description="General tone of the user persona (e.g., 'casual and humorous', 'professional and technical', 'thoughtful and reflective')"
    )
    top_25_reranked_posts: List[RerankedPost] = Field(
        description="Top 25 posts reranked from all available posts, timeline, likes, and bookmarks",
        min_length=1,
        max_length=25
    )


class ContextAgent:
    """Agent that creates context cards from user data."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "grok-4-1-fast-non-reasoning"
    ):
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY required")
        self.model = model
        self.client = Client(api_key=self.api_key)
        self._post_lookup: dict[str, dict] = {}  # Cache for post lookup

    def _add_posts_to_lookup(self, posts: list, source: str, lookup: dict) -> None:
        """Helper to add posts to lookup dictionary with composite key (source.id)."""
        for post in posts:
            post_id = post.get("id", "")
            if post_id:
                # Use composite key: source.id
                composite_key = f"{source}.{post_id}"
                lookup[composite_key] = {
                    "text": post.get("text", ""),
                    "source": source,
                    "original_id": post_id,
                    "created_at": post.get("created_at", ""),
                    "metrics": post.get("public_metrics", {}),
                    "full_data": post
                }

    def _build_post_lookup(self, user_data: dict) -> dict[str, dict]:
        """Build a lookup dictionary mapping post_id -> original post data."""
        lookup = {}
        
        # Add all post types to lookup
        self._add_posts_to_lookup(user_data.get("posts", []), "posts", lookup)
        self._add_posts_to_lookup(user_data.get("timeline", []), "timeline", lookup)
        self._add_posts_to_lookup(user_data.get("likes", []), "likes", lookup)
        self._add_posts_to_lookup(user_data.get("bookmarks", []), "bookmarks", lookup)
        
        return lookup

    def _format_post_preview(self, post: dict, source: str, max_length: int = 150) -> str:
        """Format a post preview with composite ID (source.id) and text."""
        post_id = post.get("id", "")
        text = post.get("text", "")
        preview = text[:max_length] + "..." if len(text) > max_length else text
        composite_id = f"{source}.{post_id}"
        return f"- ID: {composite_id} | {preview}"

    def _build_all_posts_list(self, posts: list, source: str) -> list:
        """Helper to build list of posts with composite IDs and previews."""
        result = []
        for post in posts:
            post_id = post.get("id", "")
            if post_id:
                text = post.get("text", "")
                preview = text[:150] + "..." if len(text) > 150 else text
                composite_id = f"{source}.{post_id}"
                result.append({
                    "id": composite_id,
                    "preview": preview,
                    "source": source
                })
        return result

    def _prepare_user_data_summary(self, user_data: dict) -> str:
        """Prepare a summary of user data for the prompt."""
        posts = user_data.get("posts", [])[:25]
        timeline = user_data.get("timeline", [])[:25]
        likes = user_data.get("likes", [])[:25]
        bookmarks = user_data.get("bookmarks", [])[:25]
        
        # Build lookup for later use
        self._post_lookup = self._build_post_lookup(user_data)
        
        # Combine all posts for reranking (just IDs and previews for prompt)
        all_posts = []
        all_posts.extend(self._build_all_posts_list(posts, "posts"))
        all_posts.extend(self._build_all_posts_list(timeline, "timeline"))
        all_posts.extend(self._build_all_posts_list(likes, "likes"))
        all_posts.extend(self._build_all_posts_list(bookmarks, "bookmarks"))
        
        # Format posts for prompt (just IDs and previews)
        posts_text = "\n".join([
            f"ID: {p['id']} [{p['source']}] Preview: {p['preview']}"
            for p in all_posts
        ])
        
        return f"""User ID: {user_data.get('user_id', 'unknown')}
Username: {user_data.get('username', 'unknown')}

LAST 25 POSTS (user's own posts):
{chr(10).join([self._format_post_preview(p, "posts") for p in posts])}

TIMELINE (Last 25 - recommended posts from X):
{chr(10).join([self._format_post_preview(t, "timeline") for t in timeline])}

LIKES (Last 25 - posts the user liked):
{chr(10).join([self._format_post_preview(l, "likes") for l in likes])}

BOOKMARKS (Last 25 - posts the user bookmarked):
{chr(10).join([self._format_post_preview(b, "bookmarks") for b in bookmarks])}

ALL POSTS FOR RERANKING ({len(all_posts)} total):
{posts_text}"""

    def _create_prompt(self, user_data_summary: str, username: str) -> str:
        """Create the analysis prompt."""
        return f"""Analyze the following user data from X (Twitter) and create a comprehensive context card.

{user_data_summary}

Based on this data, provide:

0. **Username**: {username} (include this in your response)

1. **General Topic/Theme**: What is the main topic or theme this user is interested in? Consider their posts, what they like, bookmark, and what appears in their timeline.

2. **Popular Memes**: Are there any memes, trending topics, or viral content patterns that appear frequently in the latest posts/timeline? If yes, describe them. If not, set to null.

3. **User Persona Tone**: What is the general tone and style of this user? Consider their writing style, engagement patterns, and content preferences. Examples: "casual and humorous", "professional and technical", "thoughtful and reflective", "enthusiastic and energetic", etc.

4. **Top 25 Reranked Posts**: From ALL the posts provided (posts, timeline, likes, bookmarks), rerank and select the top 25 most relevant/interesting posts that best represent this user's interests and persona. Consider:
   - Relevance to the user's main interests
   - Engagement metrics (likes, retweets, bookmarks)
   - Recency
   - Diversity of topics
   - Quality and representativeness

For each reranked post, provide ONLY:
- post_id: The unique composite ID in format "source.id" (e.g., "timeline.1997540906438939074", "likes.1997459097474789835")
- rank: Position 1-25
- relevance_score: A score from 0.0 to 1.0 indicating how relevant this post is to the user's persona

IMPORTANT: 
- The post_id MUST include the source prefix (posts, timeline, likes, or bookmarks) followed by a dot and the ID.
- Use the exact composite post_id from the list above (e.g., "timeline.123456", NOT just "123456").
- Include posts from ALL sources (posts, timeline, likes, bookmarks) to get a diverse mix.
- The text and source will be populated automatically from the original data.

Return the results in the specified JSON format."""

    def _enrich_reranked_posts(self, reranked_posts: List[RerankedPostInput]) -> List[RerankedPost]:
        """Enrich reranked posts with original text and source from the lookup."""
        enriched_posts = []
        for post in reranked_posts:
            composite_id = post.post_id
            
            # Try to find with composite key first
            if composite_id in self._post_lookup:
                original_data = self._post_lookup[composite_id]
                # Extract original ID from composite key
                original_id = original_data.get("original_id", composite_id.split(".")[-1] if "." in composite_id else composite_id)
                enriched_post = RerankedPost(
                    post_id=original_id,
                    text=original_data["text"],
                    source=original_data["source"],
                    rank=post.rank,
                    relevance_score=post.relevance_score
                )
                enriched_posts.append(enriched_post)
            else:
                # Fallback: try to find by scanning all entries for matching ID
                found = False
                for key, data in self._post_lookup.items():
                    if key.endswith(f".{composite_id}") or data.get("original_id") == composite_id:
                        enriched_post = RerankedPost(
                            post_id=data.get("original_id", composite_id),
                            text=data["text"],
                            source=data["source"],
                            rank=post.rank,
                            relevance_score=post.relevance_score
                        )
                        enriched_posts.append(enriched_post)
                        found = True
                        break
                
                if not found:
                    print(f"Warning: Post ID {composite_id} not found in lookup, skipping...")
        return enriched_posts

    def create_context_card(self, user_data: dict) -> ContextCard:
        """Create a context card from user data."""
        username = user_data.get("username", "unknown")
        user_data_summary = self._prepare_user_data_summary(user_data)
        prompt = self._create_prompt(user_data_summary, username)
        
        # Create chat and append messages
        chat = self.client.chat.create(model=self.model)
        chat.append(system("You are an expert at analyzing social media data to understand user personas, interests, and content preferences. Provide accurate, insightful analysis."))
        chat.append(user(prompt))
        
        # Parse response with structured output (using minimal input model)
        _, context_card_input = chat.parse(ContextCardInput)
        
        # Enrich reranked posts with original text and source
        enriched_posts = self._enrich_reranked_posts(context_card_input.top_25_reranked_posts)
        
        # Create final context card with enriched posts and username
        context_card = ContextCard(
            username=username,
            general_topic=context_card_input.general_topic,
            popular_memes=context_card_input.popular_memes,
            user_persona_tone=context_card_input.user_persona_tone,
            top_25_reranked_posts=enriched_posts
        )
        
        return context_card

    def create_context_card_json(self, user_data: dict) -> dict:
        """Create a context card and return as JSON dict."""
        context_card = self.create_context_card(user_data)
        return context_card.model_dump()


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = "user_data_DotVignesh_1009524384351096833.json"
    
    print(f"Loading user data from {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        user_data = json.load(f)
    
    print("Creating context card...")
    agent = ContextAgent()
    context_card = agent.create_context_card(user_data)
    
    # print("\n" + "="*60)
    # print("CONTEXT CARD")
    # print("="*60)
    # print(f"\n👤 Username: {context_card.username}")
    # print(f"\n📌 General Topic: {context_card.general_topic}")
    # print(f"\n🎭 User Persona Tone: {context_card.user_persona_tone}")
    
    # if context_card.popular_memes:
    #     print(f"\n🔥 Popular Memes: {context_card.popular_memes}")
    # else:
    #     print(f"\n🔥 Popular Memes: None detected")
    
    # print(f"\n📊 Top 25 Reranked Posts:")
    # print("-" * 60)
    # for post in context_card.top_25_reranked_posts:
    #     print(f"\nRank #{post.rank} (Score: {post.relevance_score:.3f}) [{post.source}]")
    #     print(f"ID: {post.post_id}")
    #     print(f"Text: {post.text[:150]}..." if len(post.text) > 150 else f"Text: {post.text}")
    
    # Save to JSON
    output_file = json_file.replace(".json", "_context_card.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(context_card.model_dump(), f, indent=2, ensure_ascii=False)
    
    print(f"\nContext card saved to: {output_file}")

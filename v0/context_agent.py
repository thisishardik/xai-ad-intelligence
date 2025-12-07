"""
Context Agent for User Persona Analysis
Analyzes user's posts, timeline, likes, and bookmarks to create a context card.
"""

import json
from typing import List, Optional, Union
from dataclasses import dataclass, field, asdict
from xai_sdk import Client
from xai_sdk.chat import system, user

from config import XAI_API_KEY, DEFAULT_MODEL


@dataclass
class RerankedPost:
    """A reranked post with its score and full data."""
    post_id: str
    text: str
    source: str
    rank: int
    relevance_score: float


@dataclass
class ContextCard:
    """Context card containing user persona analysis."""
    username: str
    user_id: str
    general_topic: str
    user_persona_tone: str
    popular_memes: Optional[str] = None
    top_25_reranked_posts: List[RerankedPost] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "username": self.username,
            "user_id": self.user_id,
            "general_topic": self.general_topic,
            "popular_memes": self.popular_memes,
            "user_persona_tone": self.user_persona_tone,
            "top_25_reranked_posts": [
                {
                    "post_id": p.post_id,
                    "text": p.text,
                    "source": p.source,
                    "rank": p.rank,
                    "relevance_score": p.relevance_score
                }
                for p in self.top_25_reranked_posts
            ]
        }


class ContextAgent:
    """Agent that creates context cards from user data."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = None
    ):
        self.api_key = api_key or XAI_API_KEY
        if not self.api_key:
            raise ValueError("XAI_API_KEY required")
        self.model = model or DEFAULT_MODEL
        self.client = Client(api_key=self.api_key)
        self._post_lookup: dict[str, dict] = {}

    def _add_posts_to_lookup(self, posts: list, source: str, lookup: dict) -> None:
        """Helper to add posts to lookup dictionary with composite key (source.id)."""
        for post in posts:
            post_id = post.get("id", "")
            if post_id:
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
                result.append({
                    "id": f"{source}.{post_id}",
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
        
        self._post_lookup = self._build_post_lookup(user_data)
        
        all_posts = []
        all_posts.extend(self._build_all_posts_list(posts, "posts"))
        all_posts.extend(self._build_all_posts_list(timeline, "timeline"))
        all_posts.extend(self._build_all_posts_list(likes, "likes"))
        all_posts.extend(self._build_all_posts_list(bookmarks, "bookmarks"))
        
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

Based on this data, provide a JSON response with the following structure:
{{
    "username": "{username}",
    "general_topic": "<main topic/theme the user is interested in>",
    "popular_memes": "<popular memes or trending content patterns, or null if none>",
    "user_persona_tone": "<general tone: casual and humorous, professional and technical, etc.>",
    "top_25_reranked_posts": [
        {{
            "post_id": "<source.id format e.g. timeline.123456>",
            "rank": <1-25>,
            "relevance_score": <0.0-1.0>
        }}
    ]
}}

IMPORTANT: 
- The post_id MUST include the source prefix (posts, timeline, likes, or bookmarks) followed by a dot and the ID.
- Include posts from ALL sources to get a diverse mix.
- Rank by relevance to user's persona and interests.

Return ONLY the JSON, no other text."""

    def _enrich_reranked_posts(self, reranked_posts: list) -> List[RerankedPost]:
        """Enrich reranked posts with original text and source from the lookup."""
        enriched_posts = []
        for post in reranked_posts:
            composite_id = post.get("post_id", "")
            
            if composite_id in self._post_lookup:
                original_data = self._post_lookup[composite_id]
                original_id = original_data.get("original_id", composite_id.split(".")[-1])
                enriched_posts.append(RerankedPost(
                    post_id=original_id,
                    text=original_data["text"],
                    source=original_data["source"],
                    rank=post.get("rank", 0),
                    relevance_score=post.get("relevance_score", 0.5)
                ))
            else:
                # Fallback search
                for key, data in self._post_lookup.items():
                    if key.endswith(f".{composite_id}") or data.get("original_id") == composite_id:
                        enriched_posts.append(RerankedPost(
                            post_id=data.get("original_id", composite_id),
                            text=data["text"],
                            source=data["source"],
                            rank=post.get("rank", 0),
                            relevance_score=post.get("relevance_score", 0.5)
                        ))
                        break
        return enriched_posts

    def create_context_card(self, user_data: Union[dict, 'UserData']) -> ContextCard:
        """
        Create a context card from user data.
        
        Args:
            user_data: Either a dict or UserData object containing posts, timeline, likes, bookmarks
            
        Returns:
            ContextCard with analyzed user persona
        """
        # Convert UserData to dict if needed
        if hasattr(user_data, 'to_dict'):
            user_data = user_data.to_dict()
        
        username = user_data.get("username", "unknown")
        user_id = user_data.get("user_id", "unknown")
        user_data_summary = self._prepare_user_data_summary(user_data)
        prompt = self._create_prompt(user_data_summary, username)
        
        # Create chat and get response
        chat = self.client.chat.create(model=self.model)
        chat.append(system("You are an expert at analyzing social media data to understand user personas. Return only valid JSON."))
        chat.append(user(prompt))
        
        response = chat.sample()
        content = response.content.strip()
        
        # Extract JSON if wrapped in code blocks
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Fallback parsing
            parsed = {
                "username": username,
                "general_topic": "General interests",
                "popular_memes": None,
                "user_persona_tone": "Casual",
                "top_25_reranked_posts": []
            }
        
        # Enrich reranked posts
        enriched_posts = self._enrich_reranked_posts(
            parsed.get("top_25_reranked_posts", [])
        )
        
        return ContextCard(
            username=username,
            user_id=user_id,
            general_topic=parsed.get("general_topic", "General interests"),
            popular_memes=parsed.get("popular_memes"),
            user_persona_tone=parsed.get("user_persona_tone", "Casual"),
            top_25_reranked_posts=enriched_posts
        )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        print(f"Loading user data from {json_file}...")
        with open(json_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
        
        print("Creating context card...")
        agent = ContextAgent()
        context_card = agent.create_context_card(user_data)
        
        print(f"\n✓ Context card created for @{context_card.username}")
        print(f"  Topic: {context_card.general_topic}")
        print(f"  Tone: {context_card.user_persona_tone}")
        print(f"  Posts analyzed: {len(context_card.top_25_reranked_posts)}")
        
        # Save to JSON
        output_file = json_file.replace(".json", "_context_card.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(context_card.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved to: {output_file}")
    else:
        print("Usage: python context_agent.py <user_data.json>")

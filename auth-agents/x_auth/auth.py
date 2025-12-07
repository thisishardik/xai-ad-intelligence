import os
import json
import requests
from dotenv import load_dotenv
from xdk import Client
from xdk.oauth2_auth import OAuth2PKCEAuth

# Load environment variables from .env file
load_dotenv()

CLIENT_ID = os.environ["X_CLIENT_ID"]
print("CLIENT_ID =", CLIENT_ID)

# 1. Configure PKCE OAuth
auth = OAuth2PKCEAuth(
    client_id=CLIENT_ID,             # from dev portal
    redirect_uri="http://127.0.0.1:8000/callback",   # must match portal
    scope="tweet.read users.read offline.access bookmark.read like.read",
)

# 2. Get authorization URL and send user there
auth_url = auth.get_authorization_url()
print("Visit this URL in the browser:", auth_url)

# In a real web app, you'd redirect the user to auth_url and your
# /callback route would receive the full URL with ?code=...&state=...

callback_url = input("Paste the full callback URL here: ").strip()

# 3. Exchange code for tokens
tokens = auth.fetch_token(authorization_response=callback_url)
access_token = tokens["access_token"]

# 4. Create XDK client with user access token
client = Client(token=tokens)   # or Client(bearer_token=access_token)

# 5. Get the authenticated user
me_resp = client.users.get_me()
user_id = me_resp.data['id']
username = me_resp.data.get('username', 'unknown')
print(f"\nAuthenticated as: @{username} (ID: {user_id})\n")

headers = {"Authorization": f"Bearer {access_token}"}
base_params = {
    "max_results": 25,
    "tweet.fields": "created_at,public_metrics,text,author_id"
}

# Initialize the data structure
user_data = {
    "user_id": user_id,
    "username": username,
    "posts": [],
    "timeline": [],
    "likes": [],
    "bookmarks": []
}

print("Fetching user data...")

# 1. Get Posts - Posts authored by the authenticated user
print("  - Fetching posts...")
posts_url = f"https://api.x.com/2/users/{user_id}/tweets"
posts_resp = requests.get(posts_url, headers=headers, params=base_params)
if posts_resp.status_code == 200:
    posts_data = posts_resp.json()
    user_data["posts"] = posts_data.get('data', [])
    print(f"    ✓ Found {len(user_data['posts'])} posts")
else:
    print(f"    ✗ Error fetching posts: {posts_resp.status_code}")
    print(f"    Response: {posts_resp.text[:200]}")

# 2. Get Timeline - Reverse chronological list of Posts in the authenticated User's Timeline
print("  - Fetching timeline...")
timeline_url = f"https://api.x.com/2/users/{user_id}/timelines/reverse_chronological"
timeline_resp = requests.get(timeline_url, headers=headers, params=base_params)
if timeline_resp.status_code == 200:
    timeline_data = timeline_resp.json()
    user_data["timeline"] = timeline_data.get('data', [])
    print(f"    ✓ Found {len(user_data['timeline'])} timeline posts")
else:
    print(f"    ✗ Error fetching timeline: {timeline_resp.status_code}")
    print(f"    Response: {timeline_resp.text[:200]}")

# 3. Get Liked Posts - Posts liked by the authenticated user
print("  - Fetching liked posts...")
likes_url = f"https://api.x.com/2/users/{user_id}/liked_tweets"
likes_resp = requests.get(likes_url, headers=headers, params=base_params)
if likes_resp.status_code == 200:
    likes_data = likes_resp.json()
    user_data["likes"] = likes_data.get('data', [])
    print(f"    ✓ Found {len(user_data['likes'])} liked posts")
else:
    print(f"    ✗ Error fetching likes: {likes_resp.status_code}")
    print(f"    Response: {likes_resp.text[:200]}")

# 4. Get Bookmarks - Posts bookmarked by the authenticated user
print("  - Fetching bookmarks...")
bookmarks_url = f"https://api.x.com/2/users/{user_id}/bookmarks"
bookmarks_resp = requests.get(bookmarks_url, headers=headers, params=base_params)
if bookmarks_resp.status_code == 200:
    bookmarks_data = bookmarks_resp.json()
    user_data["bookmarks"] = bookmarks_data.get('data', [])
    print(f"    ✓ Found {len(user_data['bookmarks'])} bookmarks")
else:
    print(f"    ✗ Error fetching bookmarks: {bookmarks_resp.status_code}")
    print(f"    Response: {bookmarks_resp.text[:200]}")


# Save to JSON file
output_filename = f"user_data_{username}_{user_id}.json"
with open(output_filename, 'w', encoding='utf-8') as f:
    json.dump(user_data, f, indent=2, ensure_ascii=False)

print(f"\n✓ Data saved to: {output_filename}")
print(f"\nSummary:")
print(f"  Posts: {len(user_data['posts'])}")
print(f"  Timeline posts: {len(user_data['timeline'])}")
print(f"  Liked posts: {len(user_data['likes'])}")
print(f"  Bookmarks: {len(user_data['bookmarks'])}")

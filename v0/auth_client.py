"""
Auth Client Module
Handles OAuth2 PKCE flow with X API and collects user data.
Assumes server.py is running separately.
"""

import requests
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass
from typing import Optional
from xdk import Client
from xdk.oauth2_auth import OAuth2PKCEAuth

from config import X_CLIENT_ID, REDIRECT_URI, OAUTH_SCOPES, AUTH_SERVER_HOST, AUTH_SERVER_PORT


@dataclass
class UserData:
    """Container for user data from X API."""
    user_id: str
    username: str
    posts: list
    timeline: list
    likes: list
    bookmarks: list
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "posts": self.posts,
            "timeline": self.timeline,
            "likes": self.likes,
            "bookmarks": self.bookmarks
        }


class AuthClient:
    """Client for X OAuth2 PKCE authentication and user data collection."""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        scopes: Optional[str] = None
    ):
        self.client_id = client_id or X_CLIENT_ID
        self.redirect_uri = redirect_uri or REDIRECT_URI
        self.scopes = scopes or OAUTH_SCOPES
        
        if not self.client_id:
            raise ValueError("X_CLIENT_ID is required")
        
        self.auth = OAuth2PKCEAuth(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scopes,
        )
        self.access_token: Optional[str] = None
        self.xdk_client: Optional[Client] = None
    
    def get_authorization_url(self) -> str:
        """Get the OAuth authorization URL for user to visit."""
        return self.auth.get_authorization_url()
    
    def complete_auth(self, callback_url: str) -> dict:
        """
        Complete the OAuth flow with the callback URL.
        
        Args:
            callback_url: The full callback URL with code and state params
            
        Returns:
            Token dictionary containing access_token, refresh_token, etc.
        """
        tokens = self.auth.fetch_token(authorization_response=callback_url)
        self.access_token = tokens["access_token"]
        self.xdk_client = Client(token=tokens)
        return tokens
    
    def get_authenticated_user(self) -> tuple[str, str]:
        """
        Get the authenticated user's ID and username.
        
        Returns:
            Tuple of (user_id, username)
        """
        if not self.xdk_client:
            raise RuntimeError("Not authenticated. Call complete_auth() first.")
        
        me_resp = self.xdk_client.users.get_me()
        user_id = me_resp.data['id']
        username = me_resp.data.get('username', 'unknown')
        return user_id, username
    
    def fetch_user_data(self, max_results: int = 25) -> UserData:
        """
        Fetch all user data (posts, timeline, likes, bookmarks).
        
        Args:
            max_results: Maximum results per category (default 25)
            
        Returns:
            UserData object containing all fetched data
        """
        if not self.access_token:
            raise RuntimeError("Not authenticated. Call complete_auth() first.")
        
        user_id, username = self.get_authenticated_user()
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        base_params = {
            "max_results": max_results,
            "tweet.fields": "created_at,public_metrics,text,author_id"
        }
        
        user_data = UserData(
            user_id=user_id,
            username=username,
            posts=[],
            timeline=[],
            likes=[],
            bookmarks=[]
        )
        
        # Fetch Posts
        posts_url = f"https://api.x.com/2/users/{user_id}/tweets"
        posts_resp = requests.get(posts_url, headers=headers, params=base_params)
        if posts_resp.status_code == 200:
            user_data.posts = posts_resp.json().get('data', [])
        
        # Fetch Timeline
        timeline_url = f"https://api.x.com/2/users/{user_id}/timelines/reverse_chronological"
        timeline_resp = requests.get(timeline_url, headers=headers, params=base_params)
        if timeline_resp.status_code == 200:
            user_data.timeline = timeline_resp.json().get('data', [])
        
        # Fetch Likes
        likes_url = f"https://api.x.com/2/users/{user_id}/liked_tweets"
        likes_resp = requests.get(likes_url, headers=headers, params=base_params)
        if likes_resp.status_code == 200:
            user_data.likes = likes_resp.json().get('data', [])
        
        # Fetch Bookmarks
        bookmarks_url = f"https://api.x.com/2/users/{user_id}/bookmarks"
        bookmarks_resp = requests.get(bookmarks_url, headers=headers, params=base_params)
        if bookmarks_resp.status_code == 200:
            user_data.bookmarks = bookmarks_resp.json().get('data', [])
        
        return user_data


def interactive_auth() -> UserData:
    """
    Run OAuth flow and return user data, preferring auto-callback capture.
    
    Flow:
    1) Start a tiny local HTTP server to catch the callback.
    2) Open the auth URL in the default browser.
    3) On callback, complete auth, fetch user data.
    
    If auto-capture fails (timeout/port busy), falls back to manual paste.
    """
    client = AuthClient()
    auth_url = client.get_authorization_url()

    # Attempt auto-capture via local HTTP server
    callback_holder = {"url": None, "error": None}
    done = threading.Event()

    class CallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_GET(self):
            try:
                parsed = urlparse(self.path)
                qs = parse_qs(parsed.query)
                if "code" in qs and "state" in qs:
                    full_url = f"{REDIRECT_URI}?{parsed.query}"
                    callback_holder["url"] = full_url
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body><h3>Auth received. You can close this tab.</h3></body></html>")
                    done.set()
                else:
                    self.send_response(400)
                    self.end_headers()
            except Exception as e:
                callback_holder["error"] = e
                done.set()
                try:
                    self.send_response(500)
                    self.end_headers()
                except Exception:
                    pass

    class ReusableHTTPServer(HTTPServer):
        allow_reuse_address = True

    def _port_available(host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return True
            except OSError:
                return False

    def run_server():
        try:
            server = ReusableHTTPServer((AUTH_SERVER_HOST, AUTH_SERVER_PORT), CallbackHandler)
            server.timeout = 180
            while not done.is_set():
                server.handle_request()
        except Exception as e:
            callback_holder["error"] = e
            done.set()

    print("\n" + "="*60)
    print("X AUTHENTICATION (auto-callback)")
    print("="*60)

    if not _port_available(AUTH_SERVER_HOST, AUTH_SERVER_PORT):
        raise RuntimeError(
            f"Port {AUTH_SERVER_HOST}:{AUTH_SERVER_PORT} is already in use. "
            "Stop the process using it or set AUTH_SERVER_PORT to a free port (and update the X app redirect URI)."
        )

    print("Opening browser for authorization... If it doesn't open, visit:")
    print(f"{auth_url}\n")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    webbrowser.open(auth_url, new=1, autoraise=True)

    if not done.wait(timeout=180):
        callback_holder["error"] = TimeoutError("Did not receive callback within 180s")

    callback_url = callback_holder["url"]
    if callback_url:
        print("Received callback, completing auth...")
    else:
        err = callback_holder["error"]
        raise RuntimeError(
            f"Auto-callback failed: {err or 'Unknown error'}."
            " Ensure the browser completed auth and the redirect URI matches AUTH_SERVER_HOST/PORT."
        )

    print("\nExchanging tokens...")
    client.complete_auth(callback_url)

    user_id, username = client.get_authenticated_user()
    print(f"\n✓ Authenticated as: @{username} (ID: {user_id})")

    print("\nFetching user data...")
    user_data = client.fetch_user_data()

    print(f"\n✓ Data collected:")
    print(f"  Posts: {len(user_data.posts)}")
    print(f"  Timeline: {len(user_data.timeline)}")
    print(f"  Likes: {len(user_data.likes)}")
    print(f"  Bookmarks: {len(user_data.bookmarks)}")

    return user_data


if __name__ == "__main__":
    # Test interactive auth
    user_data = interactive_auth()
    print(f"\nUser data collected for @{user_data.username}")

import os
import base64
import hashlib
import secrets
from urllib.parse import urlencode

from flask import Flask, redirect, request, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ["X_CLIENT_ID"]
print("CLIENT_ID =", CLIENT_ID)

REDIRECT_URI = "http://127.0.0.1:8000/callback"
SCOPES = "tweet.read users.read offline.access"

app = Flask(__name__)
app.secret_key = secrets.token_bytes(32)

# simple in-memory store: state -> code_verifier
state_to_verifier = {}


def generate_pkce_pair():
    # code_verifier: 43–128 chars, high entropy
    verifier_bytes = secrets.token_bytes(32)
    verifier = base64.urlsafe_b64encode(verifier_bytes).decode().rstrip("=")

    # code_challenge = BASE64URL(SHA256(verifier))
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


@app.route("/")
def start_login():
    verifier, challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(16)

    # remember verifier for this state
    state_to_verifier[state] = verifier

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }

    auth_url = "https://x.com/i/oauth2/authorize?" + urlencode(params)
    return redirect(auth_url)


@app.route("/callback")
def callback():
    error = request.args.get("error")
    if error:
        return f"X returned error: {error}", 400

    code = request.args.get("code")
    state = request.args.get("state")

    if not code or not state:
        return "Missing code or state", 400

    verifier = state_to_verifier.pop(state, None)
    if verifier is None:
        return "Invalid state (CSRF check failed)", 400

    # Exchange code -> access token
    token_resp = requests.post(
        "https://api.x.com/2/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": verifier,
        },
    )
    if not token_resp.ok:
        return f"Token request failed: {token_resp.status_code} {token_resp.text}", 400

    token_json = token_resp.json()
    access_token = token_json["access_token"]

    # Use token to call X API: get me, then my tweets
    headers = {"Authorization": f"Bearer {access_token}"}

    me_resp = requests.get("https://api.x.com/2/users/me", headers=headers)
    me = me_resp.json()
    user_id = me["data"]["id"]

    tweets_resp = requests.get(
        f"https://api.x.com/2/users/{user_id}/tweets",
        headers=headers,
        params={"max_results": 10},
    )
    tweets = tweets_resp.json()

    # Return as JSON so you can just copy it
    return jsonify(
        {
            "token": {
                "access_token": access_token,
                "refresh_token": token_json.get("refresh_token"),
                "expires_in": token_json.get("expires_in"),
            },
            "me": me,
            "tweets": tweets,
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)

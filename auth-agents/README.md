# Auth Agents

This directory contains the authentication and context generation pipeline for the X AI Ad Intelligence system. Follow these steps in order to generate user data and context cards.

## Prerequisites

- Python 3.8+
- Required Python packages (install via `pip install -r requirements.txt` if available, or install individually):
  - `flask`
  - `requests`
  - `python-dotenv`
  - `xdk` (X SDK)
  - `xai-sdk`
  - `pydantic`

## Setup

### 1. Configure Environment Variables

Before running any scripts, ensure you have the required X API keys configured in the `.env` files:

**For `x_auth/.env`:**
```env
X_CLIENT_ID=your_x_client_id_here
```

**For `context_agent/.env`:**
```env
XAI_API_KEY=your_xai_api_key_here
```

> **Note:** Make sure to obtain your X Client ID from the [X Developer Portal](https://developer.twitter.com/) and your xAI API key from the xAI platform.

## Usage

### Step 1: Start the Auth Server

First, start the authentication server:

```bash
cd x_auth
python server.py
```

The server will start on `http://127.0.0.1:8000` and will:
- Generate PKCE authorization URLs
- Handle OAuth2 callbacks
- Exchange authorization codes for access tokens

Keep this server running in a terminal window.

### Step 2: Generate User Data Card

In a new terminal window, run the authentication script to generate user data:

```bash
cd x_auth
python auth.py
```

This script will:
1. Prompt you to visit an authorization URL in your browser
2. Ask you to paste the callback URL after authorization
3. Fetch user data including:
   - Posts (user's own tweets)
   - Timeline (recommended posts from X)
   - Likes (posts the user liked)
   - Bookmarks (posts the user bookmarked)
4. Save the data to a JSON file: `user_data_{username}_{user_id}.json`

### Step 3: Generate Ad Contexts JSON

After generating the user data card, run the context agent to analyze the data and create ad contexts:

```bash
cd context_agent
python agent.py [path_to_user_data.json]
```

If no path is provided, it defaults to `user_data_DotVignesh_1009524384351096833.json`.

This script will:
1. Load the user data JSON file
2. Analyze the user's posts, timeline, likes, and bookmarks
3. Create a context card with:
   - General topic/theme
   - Popular memes (if any)
   - User persona tone
   - Top 25 reranked posts by relevance
4. Save the context card to: `{user_data_filename}_context_card.json`

## Output Files

- **User Data JSON**: `user_data_{username}_{user_id}.json`
  - Contains raw user data from X API (posts, timeline, likes, bookmarks)

- **Context Card JSON**: `{user_data_filename}_context_card.json`
  - Contains analyzed context card with user persona, topics, and reranked posts

## Troubleshooting

- **Missing X_CLIENT_ID**: Ensure your `.env` file in `x_auth/` contains a valid X Client ID
- **Missing XAI_API_KEY**: Ensure your `.env` file in `context_agent/` contains a valid xAI API key
- **Server not running**: Make sure `server.py` is running before executing `auth.py`
- **Authorization errors**: Verify your X Client ID has the correct scopes and redirect URI configured in the X Developer Portal

## Directory Structure

```
auth-agents/
├── x_auth/
│   ├── .env              # X_CLIENT_ID configuration
│   ├── server.py         # OAuth2 authentication server
│   └── auth.py           # User data collection script
├── context_agent/
│   ├── .env              # XAI_API_KEY configuration
│   └── agent.py          # Context card generation script
└── README.md            # This file
```

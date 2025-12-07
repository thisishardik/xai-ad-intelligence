# Auth Agents

This directory contains the authentication and context generation pipeline for the X AI Ad Intelligence system. Follow these steps in order to generate user data and context cards.

## Prerequisites

- Python 3.8+
- Required Python packages (install via `pip install -r requirements.txt` if available, or install individually):
  - `flask`
  - `requests`
  - `httpx` (for async HTTP requests in ad_remixer and critic_agent)
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

**For `ad_remixer/.env`:**
```env
XAI_API_KEY=your_xai_api_key_here
```

**For `critic_agent/.env`:**
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

**Required:** Provide the path to your user data JSON file generated in Step 2 (e.g., `user_data_{username}_{user_id}.json`).

This script will:
1. Load the user data JSON file
2. Analyze the user's posts, timeline, likes, and bookmarks
3. Create a context card with:
   - General topic/theme
   - Popular memes (if any)
   - User persona tone
   - Top 25 reranked posts by relevance
4. Save the context card to: `{user_data_filename}_context_card.json`

### Step 4: Remix Ads to Match User Style

After generating the context card, run the ad remixer to select the best ad and rewrite it in the user's style:

```bash
cd ad_remixer
python agent.py [path_to_context_card.json]
```

**Required:** Provide the path to your context card JSON file generated in Step 3 (e.g., `{user_data_filename}_context_card.json`).

This script will:
1. Load the context card JSON file
2. Select the best ad from a list of candidate ads (currently uses example ads; modify the script to use your own ads)
3. Rewrite the selected ad into 3 parallel variants matching the user's style:
   - Variant 1: Casual, conversational style with typical slang
   - Variant 2: Authentic voice with direct benefit emphasis
   - Variant 3: Personality-matched with a different angle/hook
4. Save the remixed ads to: `remixed_ads_output.json`

**Note:** To use your own ads, modify the `example_ads` list in `agent.py` (around line 238) or pass ads programmatically using the `AdRemixerAgent` class.

### Step 5: Evaluate Ad Performance with CTR Critic

After generating remixed ads, run the critic agent to predict click-through rates:

```bash
cd critic_agent
python agent.py
```

**Note:** Before running, you'll need to modify `agent.py` to point to your files:
- Update `context_card_path` (around line 186) to point to your context card JSON file
- Update `remixed_ads_path` (around line 191) to point to your remixed ads JSON file

The script will:
1. Load the context card JSON file
2. Load the remixed ads JSON file
3. Run ensemble CTR predictions using multiple simulation runs (default: 10 runs per ad)
4. Evaluate each ad variant based on:
   - Click probability
   - Attention score
   - Relevance score
5. Calculate aggregated CTR scores with confidence intervals
6. Display the best performing ad with confidence metrics

**Note:** You can modify the product name in the script (around line 196) or pass it programmatically using the `AsyncCTRCriticAgent` class.

## Output Files

- **User Data JSON**: `user_data_{username}_{user_id}.json`
  - Contains raw user data from X API (posts, timeline, likes, bookmarks)

- **Context Card JSON**: `{user_data_filename}_context_card.json`
  - Contains analyzed context card with user persona, topics, and reranked posts

- **Remixed Ads JSON**: `remixed_ads_output.json`
  - Contains the selected ad rewritten into 3 style-matched variants
  - Includes user_id and rewritten_ads array

- **CTR Prediction Results**: Displayed in terminal
  - Shows best performing ad variant with confidence score
  - Includes detailed CTR metrics for all variants (click probability, attention, relevance)

## Troubleshooting

- **Missing X_CLIENT_ID**: Ensure your `.env` file in `x_auth/` contains a valid X Client ID
- **Missing XAI_API_KEY**: Ensure your `.env` files in `context_agent/`, `ad_remixer/`, and `critic_agent/` contain valid xAI API keys
- **Server not running**: Make sure `server.py` is running before executing `auth.py`
- **Authorization errors**: Verify your X Client ID has the correct scopes and redirect URI configured in the X Developer Portal
- **Context card not found**: Ensure Step 3 (context agent) completed successfully before running ad_remixer
- **Remixed ads not found**: Ensure Step 4 (ad remixer) completed successfully before running critic_agent

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
├── ad_remixer/
│   ├── .env              # XAI_API_KEY configuration
│   └── agent.py          # Ad remixing script (selects & rewrites ads)
├── critic_agent/
│   ├── .env              # XAI_API_KEY configuration
│   ├── agent.py          # CTR prediction script
│   ├── test_ad_data.json # Example test data
│   └── test_user_data.json # Example test data
└── README.md            # This file
```

# v0 - Ad Intelligence Pipeline

A modular, integrated pipeline for personalized ad generation and CTR prediction.

## Overview

This pipeline runs the complete flow:
1. **Auth** → Authenticate with X and fetch user data
2. **Context** → Analyze user persona (interests, tone, style)
3. **Remix** → Select best ad and generate 3 personalized variants with images
4. **Critic** → Predict CTR for each variant using ensemble simulation

## Quick Start

### 1. Setup Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure .env
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start Auth Server (in a separate terminal)

```bash
cd ../auth-agents/x_auth
python server.py
```

### 3. Run the Pipeline

```bash
# Interactive mode (full flow with OAuth)
python pipeline.py

# From existing user data JSON
python pipeline.py user_data.json

# From existing context card (skip auth + context)
python pipeline.py --context context_card.json

# With custom ads
python pipeline.py --ads my_ads.json
```

## Architecture

```
v0/
├── config.py          # Centralized configuration
├── auth_client.py     # OAuth2 PKCE flow with X API
├── context_agent.py   # User persona analysis
├── ad_remixer.py      # Ad selection & style-matched generation
├── critic_agent.py    # Ensemble CTR prediction
├── pipeline.py        # Main orchestrator
├── .env               # API keys (create from .env.example)
└── requirements.txt   # Dependencies
```

## Usage Modes

### 1. Full Interactive Pipeline

```python
from pipeline import AdIntelligencePipeline

pipeline = AdIntelligencePipeline()
result = pipeline.run_from_auth()  # Prompts for OAuth
```

### 2. From User Data

```python
from pipeline import AdIntelligencePipeline

pipeline = AdIntelligencePipeline()
result = pipeline.run_from_user_data({
    "user_id": "123",
    "username": "example",
    "posts": [...],
    "timeline": [...],
    "likes": [...],
    "bookmarks": [...]
})
```

### 3. From Context Card

```python
from pipeline import AdIntelligencePipeline

pipeline = AdIntelligencePipeline()
result = pipeline.run_from_context_card(context_card_dict)
```

### 4. Individual Agents

```python
# Context Analysis
from context_agent import ContextAgent
agent = ContextAgent()
context_card = agent.create_context_card(user_data)

# Ad Remixing
from ad_remixer import AdRemixerAgent
agent = AdRemixerAgent()
remixed = agent.remix_ads(context_card, ads_list)

# CTR Prediction
from critic_agent import CTRCriticAgent
agent = CTRCriticAgent()
prediction = agent.predict(context_card, remixed)
```

## Custom Ads

You can provide custom ads in two ways:

### 1. Via Constructor

```python
my_ads = [
    "Buy our amazing product now!",
    "Limited time offer - 50% off!",
]
pipeline = AdIntelligencePipeline(ads=my_ads)
```

### 2. Via JSON File

```bash
python pipeline.py --ads my_ads.json
```

Where `my_ads.json` contains:
```json
[
    "Buy our amazing product now!",
    "Limited time offer - 50% off!"
]
```

## Output

The pipeline produces:
- `{username}_{timestamp}_context_card.json` - User persona analysis
- `{username}_{timestamp}_remixed_ads.json` - 3 ad variants with images
- `{username}_{timestamp}_ctr_prediction.json` - CTR scores and best ad
- `{username}_{timestamp}_full_result.json` - Complete results

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `X_CLIENT_ID` | Yes | X Developer Portal Client ID |
| `XAI_API_KEY` | Yes | xAI API Key |
| `AUTH_SERVER_HOST` | No | Auth server host (default: 127.0.0.1) |
| `AUTH_SERVER_PORT` | No | Auth server port (default: 8000) |
| `DEFAULT_MODEL` | No | Grok model (default: grok-4-1-fast-non-reasoning) |
| `IMAGE_MODEL` | No | Image model (default: grok-imagine-v0p9) |
| `CTR_ENSEMBLE_RUNS` | No | Number of CTR simulations (default: 10) |

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    OAuth (server.py)                            │
│                    Running on :8000                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    auth_client.py                               │
│   • OAuth2 PKCE flow                                            │
│   • Fetch posts, timeline, likes, bookmarks                     │
│   Output: UserData                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    context_agent.py                             │
│   • Analyze user interests & persona                            │
│   • Rerank top 25 relevant posts                                │
│   Output: ContextCard                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ad_remixer.py                                │
│   • Select best matching ad                                     │
│   • Generate 3 style-matched variants                           │
│   • Create coherent images with tool calling                    │
│   Output: RemixedAdsResult                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    critic_agent.py                              │
│   • Ensemble CTR simulation (10 runs per ad)                    │
│   • Persona-based click prediction                              │
│   • Confidence scoring                                          │
│   Output: CTRPredictionResult                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Final Output                                 │
│   Best performing ad variant with confidence score              │
│   + All variants ranked by predicted CTR                        │
└─────────────────────────────────────────────────────────────────┘
```

# xAI Ad Intelligence Platform

A comprehensive AI-powered advertising platform that delivers hyper-personalized ads by analyzing user behavior, generating style-matched ad variants, and predicting click-through rates using Grok AI models.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Module Documentation](#module-documentation)
  - [v0/ - Core Pipeline](#v0---core-pipeline)
  - [ad-portal/ - Campaign Management UI](#ad-portal---campaign-management-ui)
  - [auth-agents/ - Authentication & Agents](#auth-agents---authentication--agents)
  - [xai-ad-injection/ - Chrome Extension](#xai-ad-injection---chrome-extension)
- [Getting Started](#getting-started)
- [Environment Configuration](#environment-configuration)
- [Database Schema](#database-schema)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)

---

## Overview

The xAI Ad Intelligence Platform is an end-to-end solution for creating, personalizing, and delivering advertisements on the X (Twitter) platform. The system leverages Grok AI models to:

1. **Analyze user personas** from their X activity (posts, likes, bookmarks, timeline)
2. **Select and remix ads** to match each user's unique voice and style
3. **Predict click-through rates** using ensemble persona simulation
4. **Deliver ads intelligently** based on real-time attention prediction

The platform consists of four interconnected modules that work together to create a seamless personalized advertising experience.

---

## Key Features

### Personalized Ad Generation
- **Context Analysis**: Analyzes user's posts, timeline, likes, and bookmarks to build a comprehensive persona profile
- **Style Matching**: Rewrites ad copy to match the user's natural voice and communication style
- **Multi-Variant Generation**: Creates 3 parallel ad variants with different angles and hooks

### AI-Powered Image Enhancement
- **Vision Model Analysis**: Analyzes original ad images using Grok's multimodal capabilities
- **Intelligent Enhancement**: Generates enhanced images that preserve brand identity while improving appeal
- **CTR-Optimized Selection**: Compares original vs enhanced images and selects the best performer

### Ensemble CTR Prediction
- **Persona Simulation**: Simulates user reactions using temperature-varied LLM calls
- **Statistical Robustness**: Runs multiple simulations (default: 10) per ad for confidence scoring
- **Multi-Factor Scoring**: Combines click probability, attention score, and relevance score

### Intelligent Ad Delivery
- **Attention Prediction**: Uses Grok API to predict optimal ad insertion moments
- **Scroll Telemetry**: Tracks velocity, acceleration, pauses, and scroll direction
- **Transparent UX**: Shows users why each ad was inserted via tooltips

### Campaign Management
- **Modern Dark UI**: Beautiful, X-inspired interface for campaign submission
- **AI Configuration**: Define company persona and content restrictions for LLM guidance
- **Supabase Backend**: Secure storage for campaigns and ad creatives

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         xAI AD INTELLIGENCE PLATFORM                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   AD PORTAL (UI)    │────▶│   SUPABASE DB       │◀────│   AD SERVER (API)   │
│   Next.js 15        │     │   PostgreSQL        │     │   Flask             │
│   Campaign Submit   │     │   + Storage         │     │   REST Endpoints    │
└─────────────────────┘     └─────────────────────┘     └──────────┬──────────┘
                                      │                            │
                                      │                            │
                                      ▼                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CORE PIPELINE (v0/)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │ AUTH CLIENT  │───▶│ CONTEXT      │───▶│ AD REMIXER   │───▶│ CTR       │ │
│  │              │    │ AGENT        │    │              │    │ CRITIC    │ │
│  │ OAuth2 PKCE  │    │ Persona      │    │ Style Match  │    │ Ensemble  │ │
│  │ X API Data   │    │ Analysis     │    │ Image Gen    │    │ Predict   │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───────────┘ │
│         │                   │                   │                   │       │
│         ▼                   ▼                   ▼                   ▼       │
│    UserData           ContextCard         RemixedAds         CTRPrediction │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CHROME EXTENSION (xai-ad-injection/)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │ TELEMETRY    │───▶│ ATTENTION    │───▶│ DECISION     │───▶│ AD        │ │
│  │              │    │ MODEL        │    │ ENGINE       │    │ INJECTION │ │
│  │ Scroll Track │    │ Grok API     │    │ Multi-Factor │    │ DOM Insert│ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Activity (X)
       │
       ▼
┌──────────────────┐
│ 1. AUTHENTICATION│  OAuth2 PKCE flow via auth server
│    - Posts       │  Fetches user's posts, timeline, likes, bookmarks
│    - Timeline    │
│    - Likes       │
│    - Bookmarks   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. CONTEXT       │  Grok analyzes user data to build persona
│    - Topic       │  Identifies interests, tone, memes, style
│    - Tone        │  Reranks top 25 most relevant posts
│    - Style       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 3. AD REMIXING   │  Fetches ads from Supabase, ranks by persona fit
│    - Selection   │  Rewrites best ad into 3 style-matched variants
│    - Variants    │  Generates/enhances images with CTR scoring
│    - Images      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. CTR PREDICTION│  Ensemble simulation (10 runs per ad)
│    - Simulation  │  Persona-based click probability
│    - Confidence  │  Returns best ad with confidence score
│    - Best Ad     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 5. AD DELIVERY   │  Chrome extension monitors scroll behavior
│    - Attention   │  Grok predicts optimal insertion moments
│    - Injection   │  Injects personalized ad into X feed
└──────────────────┘
```

---

## Module Documentation

### v0/ - Core Pipeline

The main processing engine that orchestrates the complete personalization flow.

#### Directory Structure

```
v0/
├── config.py           # Centralized configuration management
├── auth_client.py      # OAuth2 PKCE authentication with X API
├── context_agent.py    # User persona analysis and context card generation
├── ad_remixer.py       # Ad selection, style matching, and image generation
├── critic_agent.py     # Ensemble CTR prediction
├── pipeline.py         # Main orchestrator connecting all agents
├── ad_server.py        # Flask API server for Chrome extension
├── supabase_client.py  # Supabase database operations
├── temp_cache.py       # Temporary caching for ad queues
└── requirements.txt    # Python dependencies
```

#### Components

##### config.py - Configuration Management

Centralizes all environment variables and settings:
- API keys (XAI_API_KEY, X_CLIENT_ID)
- Auth server configuration
- Model selection (DEFAULT_MODEL, IMAGE_MODEL)
- CTR prediction settings

##### auth_client.py - OAuth2 Authentication

Handles the complete OAuth2 PKCE flow with X API:
- Generates PKCE code verifier/challenge pairs
- Manages authorization URLs and callbacks
- Fetches user data (posts, timeline, likes, bookmarks)
- Returns structured `UserData` objects

##### context_agent.py - User Persona Analysis

Analyzes user activity to build a comprehensive persona:

```python
@dataclass
class ContextCard:
    username: str
    user_id: str
    general_topic: str           # Main interests/themes
    user_persona_tone: str       # Communication style
    popular_memes: Optional[str] # Trending content patterns
    top_25_reranked_posts: List[RerankedPost]  # Most relevant posts
```

Features:
- Processes up to 25 posts from each source (posts, timeline, likes, bookmarks)
- Uses Grok to identify topics, tone, and style patterns
- Reranks posts by relevance to user's core interests

##### ad_remixer.py - Ad Selection & Generation

The most sophisticated component, handling:

1. **Ad Ranking**: Scores ads against user persona using Grok
   - Persona alignment score
   - Category match score
   - Safety score (avoid list compliance)
   - Completeness score

2. **Image Analysis**: Analyzes original ad images using vision model
   - Identifies strengths and key elements
   - Suggests improvements for the user context

3. **Variant Generation**: Creates 3 parallel ad variants
   - Variant 1: Casual, conversational with typical slang
   - Variant 2: Authentic voice with direct benefit emphasis
   - Variant 3: Personality-matched with different angle/hook

4. **Image Enhancement**: Generates new images using tool calling
   - Preserves brand identity and key visual elements
   - Applies user-relevant enhancements
   - Performs CTR comparison (original vs enhanced)

5. **CTR Scoring**: Compares image variants
   - Uses vision model to score predicted CTR
   - Selects winner based on highest score

```python
@dataclass
class RemixedAdsResult:
    user_id: str
    selected_ad: str
    selection_reasoning: str
    original_image_url: Optional[str]
    image_analysis: Optional[ImageAnalysis]
    rewritten_ads: List[AdVariant]  # 3 variants with CTR-optimized images
```

##### critic_agent.py - CTR Prediction

Ensemble simulation for statistically robust predictions:

```python
@dataclass
class CTRPredictionResult:
    user_id: str
    best_ad_index: int
    best_ad_text: str
    confidence: float           # 0.0 - 1.0
    scores: List[EnsembleCTRScore]
    total_simulations: int
```

Methodology:
- Runs multiple simulations per ad (default: 10)
- Uses temperature variation for diversity (0.5 to 2.0)
- Calculates CTR = click_prob × 0.5 + attention × 0.3 + relevance × 0.2
- Reports mean, standard deviation, and confidence intervals

##### pipeline.py - Main Orchestrator

The `AdIntelligencePipeline` class connects all components:

```python
pipeline = AdIntelligencePipeline(ads=optional_custom_ads)

# Entry points:
result = pipeline.run_from_auth()           # Full OAuth flow
result = pipeline.run_from_user_data(data)  # From existing user data
result = pipeline.run_from_context_card(cc) # From existing context card
```

Output files generated:
- `{username}_{timestamp}_context_card.json`
- `{username}_{timestamp}_remixed_ads.json`
- `{username}_{timestamp}_ctr_prediction.json`
- `{username}_{timestamp}_ctr_comparison.json` (CSV also)
- `{username}_{timestamp}_full_result.json`

##### ad_server.py - Flask API Server

REST API for serving personalized ads to the Chrome extension:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ad/<user_id>` | GET | Get best ad for user (pops from queue) |
| `/api/ads/<user_id>` | GET | Get all ad variants for user |
| `/api/generate/<user_id>` | POST | Trigger pipeline for user |
| `/api/users` | GET | List users with cached ads |
| `/api/queue/<user_id>` | GET | Get queue status |
| `/health` | GET | Health check |

Features:
- CORS enabled for Chrome extension access
- Background pre-warming of ad queues
- Automatic queue replenishment
- Served ad tracking (no duplicates)

##### supabase_client.py - Database Client

Handles all Supabase operations:
- `fetch_ads(limit)` - Get recent ads from ad_campaigns
- `fetch_relevant_ads(context_card, limit)` - Get ads filtered by user context

---

### ad-portal/ - Campaign Management UI

A modern Next.js 15 application for advertisers to submit campaigns.

#### Directory Structure

```
ad-portal/
├── app/
│   ├── page.tsx                    # Landing page
│   ├── layout.tsx                  # Root layout
│   ├── globals.css                 # Global styles
│   └── components/
│       └── AdSubmissionForm.tsx    # Main form component
├── lib/
│   └── supabaseClient.ts           # Supabase client config
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.ts
```

#### Features

- **Dark-Themed UI**: X-inspired design with neutral grays and subtle gradients
- **Responsive Design**: Works on desktop and mobile devices
- **Drag & Drop Upload**: Intuitive image upload with instant preview
- **Real-Time Validation**: Form validation before submission

#### Form Fields

| Field | Description | Required |
|-------|-------------|----------|
| Company Name | Advertiser company name | Yes |
| Ad Title | Catchy headline for the ad | Yes |
| Ad Content | Main body text of advertisement | Yes |
| Ad Creative | Image upload (drag & drop) | No |
| Company Persona | Brand voice/tone for AI generation | Yes |
| Strictly Against | Topics/words to avoid in variations | No |
| Categories | Comma-separated ad category tags | No |

#### Categories Input

Enter a comma-separated list of categories (e.g., SaaS, Fintech, Consumer Apps, AI). Spaces are trimmed automatically.

#### Supabase Integration

The form submits to Supabase:
1. Uploads image to `ad-images` storage bucket
2. Inserts metadata to `ad_campaigns` table

```typescript
// Image upload
const { data } = await supabase.storage
  .from('ad-images')
  .upload(filePath, file);

// Campaign insert
await supabase.from('ad_campaigns').insert({
  title, description, company, tagline,
  image_url, company_persona, strictly_against, categories
});
```

---

### auth-agents/ - Authentication & Agents

Modular authentication and agent implementations (alternative to v0/).

#### Directory Structure

```
auth-agents/
├── x_auth/
│   ├── server.py        # OAuth2 authentication server
│   └── auth.py          # User data collection script
├── context_agent/
│   └── agent.py         # Context card generation
├── ad_remixer/
│   ├── agent.py         # Ad remixing script
│   └── supabase_client.py
├── critic_agent/
│   ├── agent.py         # CTR prediction script
│   ├── test_ad_data.json
│   └── test_user_data.json
└── README.md
```

#### x_auth/ - OAuth Server

Flask-based OAuth2 PKCE server:

```python
# Start server
cd auth-agents/x_auth
python server.py  # Runs on http://127.0.0.1:8000
```

Endpoints:
- `/` - Initiates OAuth flow (redirects to X authorization)
- `/callback` - Handles OAuth callback, returns tokens and user data

#### Step-by-Step Flow

1. **Start Auth Server**: `python server.py`
2. **Generate User Data**: `python auth.py` - Creates `user_data_{username}_{id}.json`
3. **Create Context Card**: `python context_agent/agent.py user_data.json`
4. **Remix Ads**: `python ad_remixer/agent.py context_card.json`
5. **Predict CTR**: `python critic_agent/agent.py`

---

### xai-ad-injection/ - Chrome Extension

Intelligent ad injection for X using Grok-powered attention prediction.

#### Directory Structure

```
xai-ad-injection/
├── manifest.json           # Chrome extension manifest
├── content.js              # Main entry point
├── model.js                # Grok API integration
├── decision.js             # Ad injection decision logic
├── inject.js               # Ad card creation & rendering
├── adCard.js               # Ad card styling and display
├── api.js                  # Server API communication
├── features/
│   ├── telemetry.js        # Scroll behavior tracking
│   ├── observer.js         # Tweet observation & injection
│   └── restore.js          # Ad persistence handling
├── dist/
│   └── content.bundle.js   # Bundled output
└── package.json
```

#### How It Works

1. **Telemetry**: Tracks scroll behavior in real-time
   - Velocity (px/ms)
   - Acceleration (px/ms²)
   - Pause duration
   - Direction changes (bounces)

2. **Attention Model**: Sends features to Grok API
   ```javascript
   const features = {
     velocity, acceleration, pauseDuration,
     reverseScroll, bounce,
     tweets_since_last_ad, time_since_last_ad
   };
   const { attention_score, reason } = await getAttentionScore(features);
   ```

3. **Decision Engine**: Multi-factor evaluation
   ```javascript
   shouldInject({
     attentionScore,      // >= 0.38 threshold
     scrollingDown,       // Must be scrolling down
     timeSinceLastAd,     // >= 3000ms
     distanceSinceLastAd  // >= 600px
   });
   ```

4. **Injection**: Creates styled ad card in X feed
   - Matches X's native tweet styling
   - Shows tooltip explaining why ad was inserted
   - Handles Twitter's virtualization (re-inserts removed ads)

#### Installation

```bash
# Install dependencies
cd xai-ad-injection
npm install

# Build extension
npm run build

# Watch mode (development)
npm run watch
```

Load in Chrome:
1. Go to `chrome://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `xai-ad-injection` directory

#### Configuration

Update API key in `model.js`:
```javascript
const XAI_API_KEY = "your_xai_api_key";
```

---

## Getting Started

### Prerequisites

- **Python 3.8+** (for v0/ and auth-agents/)
- **Node.js 18.17+** (for ad-portal/ and xai-ad-injection/)
- **Supabase account** with project configured
- **X Developer account** with OAuth2 app
- **xAI API key** for Grok models

### Quick Start

#### 1. Clone and Configure

```bash
git clone https://github.com/your-repo/xai-ad-intelligence.git
cd xai-ad-intelligence

# Create environment file
cp env.example .env
# Edit .env with your API keys
```

#### 2. Set Up Supabase

Create required tables (see [Database Schema](#database-schema)) and storage bucket.

#### 3. Run the Pipeline

```bash
cd v0

# Install dependencies
pip install -r requirements.txt

# Start auth server (in separate terminal)
cd ../auth-agents/x_auth
python server.py

# Run pipeline (back in v0/)
cd ../v0
python pipeline.py  # Interactive OAuth flow
```

#### 4. Start API Server

```bash
cd v0
python ad_server.py  # Runs on http://127.0.0.1:5000
```

#### 5. Launch Ad Portal

```bash
cd ad-portal
npm install
npm run dev  # Runs on http://localhost:3000
```

#### 6. Install Chrome Extension

```bash
cd xai-ad-injection
npm install
npm run build
# Load unpacked extension in Chrome
```

---

## Environment Configuration

Create a `.env` file at the repository root:

```env
# Supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# xAI API
XAI_API_KEY=your_xai_api_key

# X / Twitter OAuth
X_CLIENT_ID=your_x_client_id
AUTH_SERVER_HOST=127.0.0.1
AUTH_SERVER_PORT=8000

# Models (optional)
DEFAULT_MODEL=grok-4-1-fast-non-reasoning
IMAGE_MODEL=grok-imagine-v0p9

# CTR Prediction (optional)
CTR_ENSEMBLE_RUNS=10
```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_URL` | Yes | - | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | - | Supabase service role key (preferred) |
| `SUPABASE_ANON_KEY` | No | - | Alternative if RLS permits anon reads |
| `XAI_API_KEY` | Yes | - | xAI API key for Grok models |
| `X_CLIENT_ID` | Yes | - | X Developer Portal Client ID |
| `AUTH_SERVER_HOST` | No | 127.0.0.1 | Auth server host |
| `AUTH_SERVER_PORT` | No | 8000 | Auth server port |
| `DEFAULT_MODEL` | No | grok-4-1-fast-non-reasoning | Text generation model |
| `IMAGE_MODEL` | No | grok-imagine-v0p9 | Image generation model |
| `CTR_ENSEMBLE_RUNS` | No | 10 | Number of CTR simulations per ad |

---

## Database Schema

### ad_campaigns Table

```sql
CREATE TABLE ad_campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  company TEXT NOT NULL,
  tagline TEXT,
  image_url TEXT,
  company_persona TEXT,
  strictly_against TEXT,
  categories TEXT[],
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID REFERENCES auth.users(id)
);
```

### personas Table (Optional)

```sql
CREATE TABLE personas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL UNIQUE,
  persona TEXT,
  strictly_against TEXT,
  categories TEXT[],
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Storage Bucket

Create a public bucket named `ad-images` for storing ad creatives:

```sql
-- In Supabase dashboard or via SQL
INSERT INTO storage.buckets (id, name, public)
VALUES ('ad-images', 'ad-images', true);
```

---

## API Reference

### Ad Server API (v0/ad_server.py)

Base URL: `http://127.0.0.1:5000`

#### GET /api/ad/{user_id}

Get the next personalized ad for a user.

**Response:**
```json
{
  "success": true,
  "ad": {
    "title": "Personalized Ad Title",
    "description": "Ad copy matched to user's style...",
    "full_content": "Complete ad text",
    "image_uri": "https://...",
    "brand": "Company Name",
    "ctr_score": 0.823,
    "confidence": 0.89
  },
  "queue_remaining": 5
}
```

#### POST /api/generate/{user_id}

Trigger ad generation pipeline for a user.

**Request Body:**
```json
{
  "context_card": { /* ContextCard object */ },
  "force_refresh": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Generated 3 ad variants",
  "queue_size": 10
}
```

#### GET /api/queue/{user_id}

Get queue status for a user.

**Response:**
```json
{
  "user_id": "username",
  "queue_size": 8,
  "served_count": 2,
  "last_updated": "2024-12-07T10:30:00Z"
}
```

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-07T10:30:00Z"
}
```

---

## Usage Examples

### Running the Full Pipeline

```bash
# Interactive mode (OAuth flow)
python pipeline.py

# From existing user data
python pipeline.py user_data.json

# From existing context card (skip auth + context)
python pipeline.py --context context_card.json

# With custom ads
python pipeline.py --ads my_ads.json

# Custom output directory
python pipeline.py --output ./results
```

### Programmatic Usage

```python
from pipeline import AdIntelligencePipeline

# Initialize
pipeline = AdIntelligencePipeline()

# Run from context card
result = pipeline.run_from_context_card({
    "username": "user123",
    "user_id": "12345",
    "general_topic": "AI and Technology",
    "user_persona_tone": "Casual and witty",
    "top_25_reranked_posts": [...]
})

# Access results
print(f"Best Ad: {result.ctr_prediction.best_ad_text}")
print(f"Confidence: {result.ctr_prediction.confidence:.1%}")
```

### Individual Agents

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

### Chrome Extension Console Logging

Open DevTools (F12) on X to see:
- Input features sent to Grok
- Attention predictions (score + reason)
- Decision evaluation logs
- Ad injection confirmations

---

## Troubleshooting

### Common Issues

#### Missing API Keys
```
ValueError: Missing required environment variables: XAI_API_KEY, X_CLIENT_ID
```
**Solution:** Ensure your `.env` file contains all required keys.

#### Supabase Connection Failed
```
SupabaseConfigError: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required
```
**Solution:** Check Supabase credentials in `.env`. Use service role key for server-side operations.

#### No Ads Returned
```
Warning: Supabase returned 0 ads
```
**Solution:** Add campaigns via the ad-portal or directly to the `ad_campaigns` table.

#### OAuth Authorization Error
```
X returned error: access_denied
```
**Solution:** Verify X_CLIENT_ID has correct scopes and redirect URI configured in X Developer Portal.

#### Chrome Extension Not Working
```
Cannot use import statement outside a module
```
**Solution:** Run `npm run build` to bundle modules. Ensure manifest points to `dist/content.bundle.js`.

### Debug Mode

Enable verbose logging:
```bash
# Pipeline with debug output
python pipeline.py --verbose

# Ad server with debug mode
FLASK_DEBUG=1 python ad_server.py
```

### Smoke Tests

```bash
# Test Supabase connection
cd v0 && python supabase_client.py

# Test auth server
curl http://127.0.0.1:8000/health

# Test ad server
curl http://127.0.0.1:5000/health
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| AI Models | Grok (grok-4-1-fast-non-reasoning, grok-imagine-v0p9) |
| Backend | Python 3.8+, Flask, httpx |
| Frontend | Next.js 15, React, TypeScript, Tailwind CSS |
| Database | Supabase (PostgreSQL) |
| Extension | Chrome Manifest V3, ES Modules |
| Auth | OAuth2 PKCE (X API) |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Notes

- **No Fallback Ads**: If Supabase returns 0 ads, the pipeline fails fast (no default ads used)
- **Environment Isolation**: Keep secrets in root `.env` only; do not commit `.env` files
- **Rate Limits**: Be mindful of X API and xAI API rate limits during development
- **Privacy**: User data is processed locally; no personal data is stored in Supabase

---

Built with Grok by xAI

# XAI Ad Intelligence - Chrome Extension

Intelligent ad injection for X (Twitter) using Grok-powered attention prediction.

## Features

- 🧠 **Attention-based insertion** - Uses Grok API to predict optimal ad timing
- 📊 **Scroll telemetry** - Tracks velocity, acceleration, pauses, and bounces
- 💡 **Transparent UX** - Tooltip shows why each ad was inserted
- 🎯 **Multi-factor decision** - Considers attention score, spacing, and timing
- 📝 **Comprehensive logging** - See all features and predictions in console

## Development Setup

### Prerequisites
- Node.js and npm installed
- Chrome browser

### Installation

1. Install dependencies:
```bash
npm install
```

2. Build the extension:
```bash
npm run build
```

This bundles all ES modules into `dist/content.bundle.js`.

### Development Workflow

**Watch mode** (auto-rebuild on file changes):
```bash
npm run watch
```

**Manual build**:
```bash
npm run build
```

### Load Extension in Chrome

1. Open Chrome and go to `chrome://extensions`
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked"
4. Select the `xai-ad-injection` directory
5. The extension is now loaded!

### Configuration

**Important:** Update the API key in `model.js`:
```javascript
const XAI_API_KEY = "YOUR_XAI_API_KEY"; // Replace with your actual key
```

## Project Structure

```
xai-ad-injection/
├── content.js              # Main entry point
├── features/
│   ├── telemetry.js       # Scroll behavior tracking
│   ├── observer.js        # Tweet observation & ad injection
│   └── restore.js         # Ad persistence handling
├── model.js               # Grok API integration
├── decision.js            # Ad injection decision logic
├── inject.js              # Ad card creation & rendering
├── dist/
│   └── content.bundle.js  # Bundled output (generated)
├── manifest.json          # Chrome extension manifest
└── package.json           # npm configuration
```

## How It Works

1. **Telemetry** tracks scroll behavior (velocity, acceleration, pauses)
2. **Observer** detects visible tweets
3. **Model** sends features to Grok API → gets attention score + reason
4. **Decision** evaluates if all conditions are met (score ≥ 0.75, spacing, timing)
5. **Inject** creates ad with tooltip showing the reason
6. **Restore** handles Twitter's virtualization (re-inserts ads if removed)

## Console Logging

Open DevTools (F12) to see:
- 🔍 Input features sent to Grok
- ✅ Attention predictions (score + reason)
- 🎯 Decision evaluation (why ad was/wasn't injected)
- 🎉 Ad injection confirmations

## Building for Production

```bash
npm run build
```

The bundled file will be in `dist/content.bundle.js` (ready for distribution).

## Troubleshooting

**"Cannot use import statement outside a module"**
- Run `npm run build` to bundle the modules
- Make sure `manifest.json` points to `dist/content.bundle.js`

**Grok API errors**
- Check that `XAI_API_KEY` is set correctly in `model.js`
- Verify API key has proper permissions

**Ads not appearing**
- Check console for decision logs
- Attention threshold might be too high (default 0.75)
- Adjust thresholds in `decision.js`

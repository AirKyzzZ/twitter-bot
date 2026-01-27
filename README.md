# Twitter Bot

AI-powered autonomous Twitter content engine that generates and posts tweets in your voice.

## 🚀 Features

### Core
- **Voice Matching**: Generates tweets that sound like you using E.H.A framework (Emotion + Hook + Action)
- **Multi-Source Ingestion**: RSS feeds, web URLs, YouTube transcripts
- **Smart Scoring**: Topic boosting/muting, relevance filtering
- **Autonomous Mode**: 24/7 daemon with smart scheduling
- **CLI Interface**: Interactive commands for drafting, posting, and monitoring

### 📊 Data-Driven Optimizations (Jan 2026)

Based on Twitter Algorithm analysis:
- **Short & Punchy**: Under 80 chars = gold, under 140 = ideal
- **Peak Timing**: Posts concentrated during 9h-14h Paris (peak engagement)
- **Media Boost**: Auto-generated images for 2x visibility
- **Quote Tweets**: 3.7% engagement vs 1.8% standard tweets
- **No Threads**: Disabled (0 threads in top 27 performers)
- **API Safe**: 15 posts/day max (500/month free tier limit)

### 🆕 New Features

- **Quote Tweets Module**: Find and quote trending tweets in your topics
- **Smart Scheduler**: Concentrates posts during peak hours (9h, 12h, 13h)
- **Trend Analysis**: Ride viral waves with trending topic detection
- **Auto Images**: Generate images from `[IMAGE: description]` suggestions
- **E.H.A Prompts**: Emotion + Hook + Action framework for viral content

## Installation

```bash
# Clone and install
git clone <repo>
cd twitter-bot
uv sync

# Or install as a tool
uv tool install .
```

## Configuration

1. Copy example files:
```bash
mkdir -p ~/.twitter-bot
cp config.example.yaml ~/.twitter-bot/config.yaml
cp .env.example .env
```

2. Edit `~/.twitter-bot/config.yaml` with your settings

3. Set environment variables in `.env`:
```bash
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
TWITTER_BEARER_TOKEN=...  # Required for quote tweets & trends
GEMINI_API_KEY=...
```

4. (Optional) Create a voice profile at `~/.twitter-bot/voice-profile.md`

## Usage

### Basic Commands

```bash
# Generate drafts from a URL
twitter-bot draft https://example.com/article

# Generate and post
twitter-bot post https://example.com/article

# Run one autonomous cycle
twitter-bot run

# Preview next planned tweets
twitter-bot dry-run

# Start 24/7 daemon mode
twitter-bot daemon

# Check status
twitter-bot status
```

### Quote Tweet Commands

```bash
# Find trending tweets to quote in your topics
twitter-bot quote-find --topic ai
twitter-bot quote-find --topic dev
twitter-bot quote-find  # All topics

# Generate quote drafts for a specific tweet
twitter-bot quote-draft https://x.com/user/status/123456789

# Post a quote tweet
twitter-bot quote-post https://x.com/user/status/123456789 --text "my hot take on this"
```

### Trend Commands

```bash
# Show current trends with relevance scores
twitter-bot trends

# Show only trends relevant to your topics
twitter-bot trends --relevant
```

### Reply Bot Commands

```bash
# Watch timeline and reply to high-scoring tweets
twitter-bot reply-watch --dry-run

# Run one reply cycle
twitter-bot reply-once --dry-run

# Human-like browser mode (100% browser, no API)
twitter-bot reply-human --dry-run

# Check reply bot status
twitter-bot reply-status

# Export browser cookies for reply bot
twitter-bot export-cookies --browser chrome
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `draft <url>` | Generate tweet drafts from URL |
| `post <url>` | Generate and post tweet from URL |
| `run` | Execute one autonomous cycle |
| `daemon` | Start continuous autonomous mode |
| `dry-run` | Preview next N planned tweets |
| `tune` | Adjust topic scoring weights |
| `status` | Show config, queue, and health |
| `quote-find` | Find trending tweets to quote |
| `quote-draft` | Generate quote tweet drafts |
| `quote-post` | Post a quote tweet |
| `trends` | Show current trends |
| `reply-watch` | Watch and reply to timeline |
| `reply-once` | Single reply cycle |
| `reply-human` | Human-like browser mode |
| `reply-status` | Show reply bot status |
| `export-cookies` | Export browser cookies |

## Configuration Options

### Schedule (config.yaml)

```yaml
schedule:
  tweets_per_day: 15          # Max posts per day (API limit safe)
  active_hours: "09:00-14:00" # Peak engagement window
  timezone: "Europe/Paris"
```

### Poster

```yaml
poster:
  max_per_day: 15        # Conservative limit for free tier
  allow_threads: false   # Disabled - data shows threads don't perform
```

## Architecture

```
src/twitter_bot/
├── cli.py              # CLI commands
├── config.py           # Configuration management
├── daemon/
│   └── scheduler.py    # Smart timing scheduler
├── generation/
│   └── generator.py    # Tweet generation with E.H.A
├── quote/              # Quote tweet module
│   ├── finder.py       # Find trending tweets
│   └── generator.py    # Generate quote responses
├── images/             # Auto image generation
│   ├── generator.py    # Main image handler
│   └── code_screenshot.py  # Code snippet screenshots
├── trends/             # Trend analysis
│   └── analyzer.py     # Detect relevant trends
├── browser/            # Browser automation
└── reply/              # Reply bot
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | API error (Twitter/LLM) |
| 4 | No content to post |

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint
uv run ruff check .

# Type check
uv run mypy src/
```

## Twitter Algorithm 2026 Insights

Key learnings incorporated:
- **Like: +30 points**, Retweet: +20, Reply: +1
- **X Premium**: 4x boost followers, 2x non-followers
- **Media**: 2x boost vs text-only
- **Decay**: Tweet loses 50% boost every 6h
- **Peak times**: 9h, 12h, 13h Paris time
- **Short content wins**: Under 80 chars = gold

## License

MIT

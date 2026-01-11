# Twitter Bot

AI-powered autonomous Twitter content engine that generates and posts tweets in your voice.

## Features

- **Voice Matching**: Generates tweets that sound like you, not a robot
- **Multi-Source Ingestion**: RSS feeds, web URLs, YouTube transcripts
- **Smart Scoring**: Topic boosting/muting, relevance filtering
- **Autonomous Mode**: 24/7 daemon with configurable posting schedule
- **CLI Interface**: Interactive commands for drafting, posting, and monitoring

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
GEMINI_API_KEY=...
```

4. (Optional) Create a voice profile at `~/.twitter-bot/voice-profile.md`

## Usage

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

# Adjust topic weights
twitter-bot tune --boost "AI" --mute "crypto"
```

## Commands

| Command | Description |
|---------|-------------|
| `draft <url>` | Generate tweet drafts from URL |
| `post <url>` | Generate and post tweet from URL |
| `run` | Execute one autonomous cycle |
| `daemon` | Start continuous autonomous mode |
| `dry-run` | Preview next N planned tweets |
| `tune` | Adjust topic scoring weights |
| `status` | Show config, queue, and health |

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
```

## License

MIT

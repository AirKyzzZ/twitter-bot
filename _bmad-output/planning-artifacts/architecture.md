---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/product-brief-twitter-bot-2026-01-11.md"
  - "_bmad-output/planning-artifacts/research/technical-viral-tweet-patterns-research-2026-01-11.md"
  - "_bmad-output/analysis/brainstorming-session-2026-01-11.md"
  - "_bmad-output/planning-artifacts/maxime-profile.md"
workflowType: 'architecture'
project_name: 'twitter-bot'
user_name: 'Maxime'
date: '2026-01-11'
status: 'complete'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements (33 total):**

| Category | Count | Scope |
|----------|-------|-------|
| Content Ingestion | 6 | Web URLs, YouTube transcripts, RSS feeds, deduplication |
| Content Scoring | 4 | Topic boost/mute, relevance scoring, selection |
| Voice Generation | 4 | Profile loading, draft generation, tone matching |
| Twitter Integration | 4 | Auth, posting, draft-only mode |
| Autonomous Operation | 5 | Run cycles, daemon mode, scheduling, dry-run |
| Configuration | 4 | YAML config, env vars, live tuning |
| CLI Interface | 6 | Commands, output formats, exit codes, verbosity |

**Non-Functional Requirements (14 total):**

| Category | Key Requirements |
|----------|------------------|
| Performance | < 2 min end-to-end, < 30s RSS processing, < 60s LLM response |
| Security | Env var credentials, no secret logging, config permission checks |
| Integration | 3x retry with backoff, timeout handling, rate limit respect |
| Reliability | Daemon self-recovery, state persistence, graceful shutdown, health checks |

### Scale & Complexity

- **Primary domain:** Backend CLI with external API integrations
- **Complexity level:** Low (single user, focused feature set)
- **Estimated architectural components:** 6-8 core modules

### Technical Constraints & Dependencies

| Constraint | Impact |
|------------|--------|
| Python 3.11+ | Language choice locked |
| Gemini 2.5 Flash | LLM provider (free tier) |
| Twitter API v2 Free tier | Rate limits, feature constraints |
| Single-user operation | Simplifies auth, state, concurrency |
| Local/VPS deployment | No cloud-native requirements |

### Cross-Cutting Concerns Identified

1. **Configuration Management** - YAML with env var interpolation, runtime tuning
2. **Error Handling & Resilience** - Graceful failures, retry logic, daemon recovery
3. **Logging & Observability** - Structured logs, verbosity levels, health checks
4. **State Persistence** - Deduplication history, last posts, queue state across restarts
5. **Rate Limiting** - Twitter API compliance to avoid suspension

## Starter Template Evaluation

### Primary Technology Domain

Python CLI Tool (hybrid interactive + autonomous daemon) based on project requirements analysis.

### Starter Options Considered

| Approach | Verdict |
|----------|---------|
| Cookiecutter templates | Too heavyweight for focused CLI tool |
| Poetry + Click | Click is lower-level than Typer, Poetry slower than uv |
| uv + Typer + Ruff | Modern, fast, right-sized for project |

### Selected Approach: uv + Typer + Ruff Stack

**Rationale:**
- uv provides fast, modern Python project management with lockfile support
- Typer gives type-hint-driven CLI with built-in Rich integration (matches PRD requirement for colored output)
- Ruff consolidates linting/formatting in a single fast tool
- Minimal boilerplate, maximum control for a focused CLI tool

**Initialization Commands:**

```bash
uv init twitter-bot
cd twitter-bot
uv add typer[all] pyyaml pydantic-settings httpx feedparser google-generativeai apscheduler tenacity
uv add --dev ruff pytest pytest-asyncio
```

### Architectural Decisions Provided by Starter

**Language & Runtime:**
- Python 3.11+ (per PRD constraint)
- src/ layout for clean imports

**CLI Framework:**
- Typer 0.21.1 with Rich integration
- Automatic help generation from type hints
- Subcommand structure for `draft`, `post`, `run`, `daemon`, `tune`, `status`

**Dependency Management:**
- uv for fast installs and universal lockfile
- pyproject.toml as single source of truth

**Code Quality:**
- Ruff for linting (replaces Flake8) and formatting (replaces Black)
- pytest for testing

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- State persistence strategy
- LLM integration pattern
- Configuration architecture
- Daemon scheduling approach

**Important Decisions (Shape Architecture):**
- HTTP client patterns
- Error handling strategy
- Logging approach

**Deferred Decisions (Post-MVP):**
- Performance feedback loop storage
- Multi-provider LLM orchestration
- Metrics/analytics collection

### State Persistence

| Decision | Choice |
|----------|--------|
| **Storage Format** | JSON files |
| **Location** | `~/.twitter-bot/` |
| **Files** | `state.json` (history, deduplication), `queue.json` (pending) |
| **Rationale** | Simple, zero dependencies, human-readable for debugging |

### LLM Integration

| Decision | Choice |
|----------|--------|
| **Pattern** | Thin abstraction layer |
| **Interface** | `LLMProvider` protocol |
| **Implementation** | `GeminiProvider` (MVP), extensible to OpenAI/Claude |
| **Rationale** | Easy provider swapping without touching generation logic |

### HTTP & External Services

| Decision | Choice |
|----------|--------|
| **Base Client** | httpx |
| **Pattern** | Thin domain wrappers |
| **Wrappers** | `TwitterClient`, `RSSClient`, `WebExtractor`, `YouTubeExtractor` |
| **Rationale** | Consistent HTTP handling, domain logic isolated |

### Configuration

| Decision | Choice |
|----------|--------|
| **Library** | Pydantic Settings |
| **Format** | YAML file + environment variables |
| **Location** | `~/.twitter-bot/config.yaml` |
| **Features** | Type-safe validation, automatic env var interpolation |
| **Rationale** | Modern Python standard, minimal validation code |

### Daemon & Scheduling

| Decision | Choice |
|----------|--------|
| **Library** | APScheduler |
| **Pattern** | Background scheduler with interval triggers |
| **Features** | Cron-like scheduling, active hours respect, graceful shutdown |
| **Rationale** | Handles scheduling complexity, built-in signal handling |

### Error Handling & Resilience

| Decision | Choice |
|----------|--------|
| **Retry Library** | tenacity |
| **Pattern** | Decorator-based retries |
| **Config** | 3 attempts, exponential backoff (4s → 60s max) |
| **Scope** | All external API calls (Twitter, LLM, RSS, Web) |
| **Rationale** | Clean code, configurable, works across all integrations |

### Logging & Observability

| Decision | Choice |
|----------|--------|
| **Library** | stdlib logging + Rich handler |
| **Output** | Colored terminal output via Rich |
| **Verbosity** | `-v` (INFO), `-vv` (DEBUG) flags |
| **Rationale** | No extra deps, leverages existing Rich integration |

## Implementation Patterns & Consistency Rules

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Functions/Variables | snake_case | `get_tweet_drafts`, `tweet_id` |
| Classes | PascalCase | `TweetGenerator`, `GeminiProvider` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY_ATTEMPTS` |
| Files/Modules | snake_case | `twitter_client.py` |
| JSON keys | snake_case | `{"posted_at": "..."}` |

### Module Organization

**By Domain (functional boundaries):**

```
src/twitter_bot/
├── __init__.py
├── __main__.py           # Entry: python -m twitter_bot
├── cli.py                # Typer commands
├── config.py             # Pydantic Settings
├── exceptions.py         # Custom exception hierarchy
├── sources/
│   ├── __init__.py
│   ├── rss.py            # RSSClient
│   ├── web.py            # WebExtractor
│   └── youtube.py        # YouTubeExtractor
├── scoring/
│   ├── __init__.py
│   └── scorer.py         # ContentScorer
├── generation/
│   ├── __init__.py
│   ├── provider.py       # LLMProvider protocol
│   ├── gemini.py         # GeminiProvider
│   └── generator.py      # TweetGenerator
├── twitter/
│   ├── __init__.py
│   └── client.py         # TwitterClient
├── daemon/
│   ├── __init__.py
│   └── scheduler.py      # APScheduler setup
└── state/
    ├── __init__.py
    └── manager.py        # JSON state read/write
```

### Error Handling

**Exception Hierarchy:**

```python
class TwitterBotError(Exception): pass
class ConfigError(TwitterBotError): pass
class TwitterAPIError(TwitterBotError): pass
class LLMProviderError(TwitterBotError): pass
class SourceError(TwitterBotError): pass
class StateError(TwitterBotError): pass
```

**Rules:**
- Domain code raises specific exceptions
- CLI layer catches and maps to exit codes + Rich error output
- Never catch generic `Exception` in domain code

### Logging

- Simple f-string messages: `logger.info(f"Tweet {tweet_id} posted")`
- Rich formatting only for user-facing CLI output
- Levels: DEBUG (internals), INFO (operations), WARNING (recoverable), ERROR (failures)

### Testing

- Mirrored structure: `tests/` mirrors `src/twitter_bot/`
- Naming: `test_<module>.py`
- pytest with pytest-asyncio for async tests

## Final Project Structure

```
twitter-bot/
├── pyproject.toml
├── uv.lock
├── .env.example
├── config.example.yaml
├── README.md
├── src/
│   └── twitter_bot/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── exceptions.py
│       ├── sources/
│       ├── scoring/
│       ├── generation/
│       ├── twitter/
│       ├── daemon/
│       └── state/
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── sources/
    ├── scoring/
    ├── generation/
    ├── twitter/
    ├── daemon/
    └── state/
```

## Implementation Sequence

1. **Project scaffold** - uv init, dependencies, pyproject.toml
2. **Config module** - Pydantic Settings, YAML loading
3. **State module** - JSON persistence, deduplication
4. **HTTP clients** - httpx wrappers for each domain
5. **LLM abstraction** - Provider protocol + Gemini implementation
6. **Content pipeline** - Sources → Scoring → Generation
7. **Twitter integration** - Post, rate limiting
8. **CLI commands** - Typer app with all subcommands
9. **Daemon mode** - APScheduler, graceful shutdown

---

_Architecture complete. Ready for implementation._

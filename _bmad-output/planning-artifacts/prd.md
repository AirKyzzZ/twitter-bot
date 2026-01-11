---
stepsCompleted: ["step-01-init", "step-02-discovery", "step-03-success", "step-04-journeys", "step-05-domain", "step-06-innovation", "step-07-project-type", "step-08-scoping", "step-09-functional", "step-10-nonfunctional", "step-11-polish"]
inputDocuments:
  - "_bmad-output/planning-artifacts/product-brief-twitter-bot-2026-01-11.md"
  - "_bmad-output/planning-artifacts/research/technical-viral-tweet-patterns-research-2026-01-11.md"
  - "_bmad-output/analysis/brainstorming-session-2026-01-11.md"
  - "_bmad-output/planning-artifacts/maxime-profile.md"
workflowType: "prd"
documentCounts:
  briefs: 1
  research: 1
  brainstorming: 1
  profile: 1
  projectDocs: 0
classification:
  projectType: "cli_tool"
  domain: "developer_tools"
  complexity: "low"
  projectContext: "greenfield"
---

# Product Requirements Document - twitter-bot

**Author:** Maxime Mansiet
**Date:** 2026-01-11

## Executive Summary

The **twitter-bot** is an AI-powered command-line interface (CLI) tool designed to autonomously generate and post high-quality, viral-ready content to Twitter/X. It serves as a force multiplier for Maxime Mansiet, automating the research, drafting, and publishing process while adhering to rigorous standards for "high-signal" content. The tool leverages advanced prompt engineering and specific "viral patterns" to transform various inputs (URLs, YouTube videos, thoughts) into engaging threads or tweets that mimic the user's authentic voice.

**Core Value Proposition:**
*   **Time Efficiency:** Reduces hours of content creation to minutes.
*   **Quality Consistency:** Ensures every post meets a high bar for insight and engagement potential.
*   **Automation:** Handles the end-to-end workflow from ideation to publication.

## Project Classification

*   **Project Type:** CLI Tool (Python-based)
*   **Domain:** Developer Tools / Social Media Automation
*   **Complexity:** Low (Focused feature set, single user)
*   **Context:** Greenfield (New project)

## Success Criteria

### User Success

*   **Authenticity of Voice:** The primary "Aha!" moment is when the bot generates a tweet that is indistinguishable from something you would have written yourself.
*   **High Signal Content:** The bot consistently produces insights that maintain your reputation for quality, rather than "engagement bait."
*   **Creative Spark:** The bot identifies unique angles or "hooks" that provide fresh perspectives on existing content.

### Business Success

*   **Engagement Growth:** A measurable increase in views, likes, retweets, and comments compared to your current baseline.
*   **Follower Velocity:** An uptick in the rate of new followers gained per week.
*   **Community Building:** Increased meaningful interactions in the comments/replies of the generated posts.

### Technical Success

*   **End-to-End Automation:** The CLI successfully handles the full cycle: Finding an idea → Writing it well → Sending it to Twitter automatically.
*   **Idea Extraction Quality:** High accuracy in identifying the "nugget" of value from long-form sources (RSS, YouTube, Web).
*   **API Reliability:** Stable integration with the Twitter/X API for automated posting.

### Measurable Outcomes

*   **Edit Rate:** 80% of generated tweets are "post-ready" with zero or minor manual edits.
*   **Engagement Lift:** Target a 15-20% increase in average engagement metrics within the first 30 days of deployment.
*   **Automation Speed:** The cycle from "Source Input" to "Posted Tweet" completes in under 2 minutes.

## Product Scope

### MVP - Minimum Viable Product

*   **CLI Core:** A command-line tool for both manual and autonomous operation.
*   **Tone Engine:** Uses Maxime's profile and viral patterns to draft 3-5 high-signal tweets.
*   **Auto-Post:** Direct integration to post the selected draft to Twitter/X.
*   **Source Support:** Web URLs, YouTube transcripts, and RSS feeds.
*   **Autonomous Mode:** RSS ingestion, content scoring, and 24/7 autonomous posting without user input.
*   **Content Intelligence:** Topic boosting/muting and deduplication to maintain quality.

### Growth Features (Post-MVP)

*   **Evergreen Fallback:** Knowledge base for low-news cycles.
*   **Performance Feedback:** Automatically tracking which tweets perform best to "learn" and improve future drafts.

### Vision (Future)

*   **Visual Assets:** Generating memes or infographics to accompany the text.
*   **Multi-Agent Workflow:** Separate agents for deep research, copywriting, and "vibe-checking."
*   **Multi-Persona:** Supporting different "voices" for different accounts or sub-niches.

## User Journeys

### 1. The "Content Factory" Journey (Primary Autonomous Loop)

*   **Persona:** Maxime (Offline/Vacation).
*   **Context:** The system is running in "Auto-Pilot" mode. The goal is 30 tweets/day (approx. 1 every 30-45 mins during active hours).
*   **Trigger:** Scheduled interval (e.g., every 30 mins).
*   **Action (System):**
    1.  **Ingest:** The bot fetches the latest items from a curated list of high-quality RSS feeds (TechCrunch, Hacker News, specific engineering blogs).
    2.  **Filter & Score:** It analyzes 50+ new items. It discards low-relevance topics (crypto, politics) based on config. It scores the remaining ones for "Viral Potential" and "Relevance to Maxime."
    3.  **Select:** It picks the top-scored item that hasn't been posted yet.
    4.  **Draft:** It generates a tweet (or thread) extracting the core insight. It applies a specific "Viral Pattern" (e.g., "Contrarian Take," "The 'How-To' Summary").
    5.  **Publish:** It posts immediately to Twitter/X.
*   **Outcome:** A steady stream of high-signal content is maintained throughout the day without human intervention.
*   **Requirements:** Robust Scheduler, RSS Ingestion Engine, Relevance Scoring Algorithm, Content History (Deduplication).

### 2. The "Calibration" Journey (Setup & Tuning)

*   **Persona:** Maxime (The Engineer).
*   **Context:** Maxime notices the bot is posting too much about "JavaScript Frameworks" and not enough about "AI Architecture."
*   **Action:** Maxime edits the `config.yaml` or runs a command: `twitter-bot tune --boost "AI Architecture" --mute "React"`.
*   **System Response:** The bot updates its scoring weights immediately.
*   **Verification:** Maxime runs `twitter-bot dry-run`. The output shows the next 10 planned tweets are now aligned with the new focus.
*   **Outcome:** The "editorial direction" is corrected with high-level directives, not micro-management.
*   **Requirements:** Dynamic Configuration, Weighted Scoring System, Dry-Run/Simulation Capability.

### 3. The "Evergreen" Journey (Low-News Cycle)

*   **Persona:** The System (Autonomous Agent).
*   **Context:** It's a slow Sunday. RSS feeds are quiet. The queue for "News" is empty.
*   **Action (System):**
    1.  **Detect:** The bot recognizes the "News" queue is dry.
    2.  **Switch Strategy:** It queries its "Evergreen Knowledge Base" (a collection of Maxime's beliefs, timeless engineering principles, or older "Idea Bank" items).
    3.  **Remix:** It takes a core principle (e.g., "Simple is better than complex") and generates a new standalone tweet using a "Quote" or "Aphorism" pattern.
    4.  **Publish:** The schedule is maintained despite the lack of news.
*   **Outcome:** Consistency is protected even when external inputs fail.
*   **Requirements:** "Evergreen" Content Database, Fallback Logic, Multi-Mode Content Generation.

### Journey Requirements Summary

*   **Autonomous Scheduler:** Capable of triggering actions at high frequency (30/day).
*   **Data Pipeline:**
    *   RSS Feed Manager (Add/Remove/Group).
    *   Content Filter & Scorer (The "Brain" that decides what is worth posting).
    *   Deduplication Layer (Don't post the same news twice).
*   **Content Engine:**
    *   Multi-Format Generator (News commentary, Threads, Evergreen insights).
    *   Tone/Voice Adaptation.
*   **Configuration Interface:** CLI for tuning weights, adding sources, and managing the "Idea Bank."

## Innovation & Novel Patterns

### Detected Innovation Areas

1. **Personalized Voice Cloning**
   - Unlike generic content generators, this tool is trained on YOUR writing patterns, beliefs, and communication style
   - The "Aha!" moment: content indistinguishable from what you'd write yourself
   - This requires deep profile integration, not just prompt templates

2. **Accessible Autonomous Agent**
   - Enterprise automation tools (Hootsuite, Sprout Social AI, etc.) cost $100-500+/month
   - This is a self-hosted, personal tool with zero ongoing cost beyond API usage
   - Full control over the "editorial brain" - your config, your rules

3. **Editorial AI with Taste**
   - The system doesn't just generate content - it makes value judgments
   - Filters out low-signal topics, scores for viral potential AND personal relevance
   - An AI that understands "high-signal" vs "engagement bait"

### Market Context & Competitive Landscape

- **Expensive Enterprise Tools:** Buffer, Hootsuite, Sprout Social - cost-prohibitive, designed for teams
- **Generic AI Writers:** ChatGPT, Jasper, Copy.ai - produce generic output, no voice matching
- **The Gap:** No affordable tool that writes *like you* with autonomous posting capability

### Validation Approach

- **Voice Accuracy Test:** Can you distinguish bot-generated tweets from your own in a blind test?
- **Engagement Parity:** Do AI-generated posts perform equal to or better than manual posts?
- **Edit Rate Metric:** Target 80% "post-ready" with zero edits

## CLI Tool Specific Requirements

### Project-Type Overview

The twitter-bot is a **hybrid CLI tool** - designed for both interactive use (calibration, dry-runs, manual posting) and autonomous scriptable execution (cron-driven Content Factory mode).

### Command Structure

| Command | Mode | Description |
|---------|------|-------------|
| `twitter-bot post <url>` | Interactive | Generate and post from a specific URL |
| `twitter-bot draft <url>` | Interactive | Generate drafts without posting |
| `twitter-bot dry-run` | Interactive | Preview next N planned tweets |
| `twitter-bot run` | Scriptable | Execute one autonomous cycle |
| `twitter-bot daemon` | Scriptable | Start continuous autonomous mode |
| `twitter-bot tune --boost <topic> --mute <topic>` | Interactive | Adjust scoring weights |
| `twitter-bot status` | Both | Show queue status, last posts, health check |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Configuration error |
| `3` | Twitter API error |
| `4` | No content to post (empty queue) |

### Output Formats

*   **Interactive Mode:** Colored terminal output using `rich` library for readability
*   **Scriptable Mode:** Plain text / JSON output for parsing by cron or monitoring tools
*   **Flag:** `--json` forces JSON output for any command

### Configuration Schema

```yaml
# ~/.twitter-bot/config.yaml
profile:
  name: "Maxime Mansiet"
  voice_file: "./maxime-profile.md"

twitter:
  api_key: "${TWITTER_API_KEY}"
  api_secret: "${TWITTER_API_SECRET}"
  access_token: "${TWITTER_ACCESS_TOKEN}"
  access_secret: "${TWITTER_ACCESS_SECRET}"

sources:
  rss_feeds:
    - url: "https://hnrss.org/frontpage"
      weight: 1.0
    - url: "https://techcrunch.com/feed/"
      weight: 0.8

scoring:
  boost_topics: ["AI", "Architecture", "Python"]
  mute_topics: ["crypto", "politics"]

schedule:
  tweets_per_day: 30
  active_hours: "08:00-22:00"
  timezone: "Europe/Paris"

evergreen:
  knowledge_base: "./evergreen/"
  fallback_probability: 0.2
```

### Scripting Support

*   **Environment Variables:** All secrets via `${VAR}` interpolation in config
*   **Cron Integration:** `twitter-bot run` exits cleanly for scheduled execution
*   **Daemon Mode:** `twitter-bot daemon` for long-running autonomous operation
*   **Logging:** Structured logs to stdout/stderr, configurable verbosity with `-v` / `-vv`
*   **Health Check:** `twitter-bot status --json` for monitoring integration

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Full Autonomous Loop - The bot must work 24/7 without user input from day one.
**Core Thesis:** The value is in autonomous operation that writes like Maxime. Both voice AND automation are essential.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Content Factory (autonomous 24/7 posting from RSS)
- Manual posting workflow (URL → bot writes → bot posts)
- Calibration via config and `tune` command

**Must-Have Capabilities:**
- `twitter-bot draft <url>` - Generate 3-5 voice-matched tweet options
- `twitter-bot post <url>` - Draft + auto-post the best option
- `twitter-bot run` - Execute one autonomous cycle (fetch → score → draft → post)
- `twitter-bot daemon` - Start continuous 24/7 autonomous operation
- `twitter-bot tune --boost <topic> --mute <topic>` - Adjust scoring live
- `twitter-bot dry-run` - Preview next N planned posts
- `twitter-bot status` - Health check and queue status
- RSS feed ingestion and content scoring
- Web URL and YouTube transcript extraction
- Voice profile integration (maxime-profile.md)
- Topic boosting/muting and deduplication
- YAML configuration with env var interpolation

**Explicitly Excluded from MVP:**
- Evergreen content fallback (low-news cycle handling)
- Performance tracking feedback loop
- Multi-format output (threads vs single tweets)
- Visual asset generation

### Post-MVP Features

**Phase 2 (Intelligence):**
- Evergreen knowledge base fallback for low-news cycles
- Viral pattern selection algorithm
- Performance tracking and feedback loop

**Phase 3 (Expansion):**
- Multi-format output (threads vs single tweets)
- Visual asset generation (memes, infographics)
- Multi-persona support for different accounts

### Risk Mitigation Strategy

**Technical Risks:**
- Voice quality may require iteration - use `draft` command for manual review initially
- Iterate on prompt engineering before enabling full autonomous mode
- Build in `--dry-run` flag for safety before committing to posts

**Operational Risks:**
- Voice Drift: Periodic recalibration of the profile/prompt to maintain authenticity
- Quality Degradation: Human review mode available; always test with `dry-run` first
- API Dependency: Graceful fallback if Twitter API changes or rate limits hit

**Resource Risks:** Solo developer
- MVP is comprehensive but focused on core autonomous loop
- External monitoring (cron, systemd) can supplement daemon mode initially

## Functional Requirements

### Content Ingestion

- **FR1:** User can provide a web URL to extract article content
- **FR2:** User can provide a YouTube URL to extract video transcript
- **FR3:** System can parse and extract the core insight from long-form content
- **FR4:** User can configure a list of RSS feed sources with weights
- **FR5:** System can fetch and parse RSS feed items automatically
- **FR6:** System can track which content has already been processed (deduplication)

### Content Scoring & Selection

- **FR7:** User can configure topics to boost (increase priority)
- **FR8:** User can configure topics to mute (filter out)
- **FR9:** System can score content items for relevance to user's interests
- **FR10:** System can select the highest-scored unprocessed item for posting

### Voice-Matched Generation

- **FR11:** System can load a voice profile document (markdown)
- **FR12:** System can generate 3-5 tweet draft options from extracted content
- **FR13:** System can apply the user's voice/tone patterns to generated content
- **FR14:** User can review generated drafts in the terminal with formatting

### Twitter Integration

- **FR15:** System can authenticate with Twitter/X API using configured credentials
- **FR16:** System can post a tweet to the authenticated account
- **FR17:** User can execute draft-only mode (no posting)
- **FR18:** User can execute draft-and-post mode (end-to-end)

### Autonomous Operation

- **FR19:** User can run `twitter-bot run` to execute one autonomous cycle (fetch → score → draft → post)
- **FR20:** User can run `twitter-bot daemon` to start continuous autonomous operation
- **FR21:** User can configure posting frequency and active hours
- **FR22:** System can run unattended without user input
- **FR23:** User can run `twitter-bot dry-run` to preview next N planned posts without posting

### Configuration

- **FR24:** User can configure Twitter API credentials via YAML file
- **FR25:** User can specify voice profile file path in configuration
- **FR26:** System can interpolate environment variables in configuration values
- **FR27:** User can run `twitter-bot tune --boost <topic> --mute <topic>` to adjust scoring live

### CLI Interface

- **FR28:** User can run `twitter-bot draft <url>` to generate drafts from specific URL
- **FR29:** User can run `twitter-bot post <url>` to generate and post from specific URL
- **FR30:** User can run `twitter-bot status` to check configuration, queue, and API health
- **FR31:** System can display colored output in interactive mode
- **FR32:** System can return appropriate exit codes for scripting
- **FR33:** User can specify output verbosity level via CLI flags

## Non-Functional Requirements

### Performance

- **NFR1:** End-to-end cycle (URL → Posted Tweet) completes in under 2 minutes
- **NFR2:** RSS feed fetch and scoring completes in under 30 seconds for 50+ items
- **NFR3:** LLM draft generation returns within 60 seconds per request

### Security

- **NFR4:** Twitter API credentials stored via environment variables, never in config files
- **NFR5:** No credentials logged to stdout/stderr at any verbosity level
- **NFR6:** Config file permissions validated (warn if world-readable)

### Integration

- **NFR7:** Twitter API failures handled gracefully with retry logic (3 attempts, exponential backoff)
- **NFR8:** LLM API timeout handled with clear error message and non-zero exit code
- **NFR9:** RSS feed failures do not crash daemon mode; skip and log, continue to next source
- **NFR10:** System respects Twitter API rate limits (avoid account suspension)

### Reliability

- **NFR11:** Daemon mode recovers from transient failures without manual restart
- **NFR12:** Content history persists across restarts (no duplicate posts after reboot)
- **NFR13:** Graceful shutdown on SIGTERM/SIGINT preserves state
- **NFR14:** Health check endpoint/command available for monitoring integration

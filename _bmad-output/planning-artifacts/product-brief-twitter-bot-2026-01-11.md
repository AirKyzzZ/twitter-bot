---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - "_bmad-output/analysis/brainstorming-session-2026-01-11.md"
  - "_bmad-output/planning-artifacts/research/technical-viral-tweet-patterns-research-2026-01-11.md"
  - "_bmad-output/planning-artifacts/maxime-profile.md"
date: 2026-01-11
author: Maxime Mansiet
---

# Product Brief: twitter-bot

## Executive Summary

**twitter-bot** is an AI-powered personal Twitter content engine designed for busy developers who want to build a strong personal brand without spending hours daily on content creation.

The bot leverages a free/low-cost stack (Twitter API + Gemini 2.5 Flash) to generate authentic, high-quality tweets that sound like the user—not a robot. It handles the volume (50+ tweets/day), while the user maintains the human touch through replies and engagement.

**Target Outcome:** Grow from current following to 10K+ followers within 6 months, establish authority in the dev/SSI space, and unlock monetization opportunities.

---

## Core Vision

### Problem Statement

Busy developers and entrepreneurs face a painful tradeoff: **either spend 2-3 hours daily creating quality Twitter content, or watch their personal brand stagnate**.

Existing solutions (Hypefury, Tweet Hunter, generic AI) either require manual writing or produce robotic, generic content that doesn't represent the user's authentic voice.

### Problem Impact

- **Lost opportunity cost:** Hours spent on tweets could be spent building
- **Inconsistent presence:** Sporadic posting kills algorithm momentum
- **Generic content:** AI-generated tweets are easily spotted and ignored
- **Missed monetization:** Without audience, there's no leverage for opportunities

### Why Existing Solutions Fall Short

| Solution               | Problem                                   |
| ---------------------- | ----------------------------------------- |
| **Scheduling tools**   | You still write everything manually       |
| **Generic AI prompts** | Sound robotic, no personal voice          |
| **Content templates**  | Everyone uses the same formulas           |
| **Ghostwriters**       | Expensive, still not your authentic voice |

### Proposed Solution

An automated content engine with:

1. **Personal Voice Layer** - Trained on existing tweets + profile to sound authentically like the user
2. **Trend-Aware Generation** - Pulls from Twitter trends, Hacker News, GitHub trending
3. **Multi-Format Output** - Single tweets, threads, polls, image tweets
4. **Quality Validation** - Checks for "Would I actually say this?" before posting
5. **Human-in-the-Loop** - User handles replies and engagement; bot handles volume

### Key Differentiators

| Differentiator                        | Why It Matters                                           |
| ------------------------------------- | -------------------------------------------------------- |
| **Free/Low-Cost Stack**               | Twitter API Free tier + Gemini Flash = $0/month to start |
| **Built by Developer, for Developer** | Can customize, extend, and optimize                      |
| **Voice-First Design**                | Not generic viral templates—authentic voice at scale     |
| **Dev/Tech Niche Focus**              | Optimized for technical content patterns                 |
| **Educational Value**                 | Can teach dev topics while building brand                |

---

## Target Users

### Primary User

**Maxime Mansiet** - 19-year-old Full-Stack Developer & Serial Entrepreneur

| Attribute           | Details                                                     |
| ------------------- | ----------------------------------------------------------- |
| **Role**            | Developer at Verana & 2060.io, CEO of Klyx, Co-founder PKBA |
| **Technical Level** | Advanced (can build, modify, and maintain the bot)          |
| **Time Available**  | ~30 min/day for Twitter (replies, engagement only)          |
| **Current Pain**    | Running 4+ projects, no bandwidth for 50+ daily tweets      |

**Problem Experience:**

- Knows consistent Twitter presence is valuable but can't sustain it
- Building custom solution from scratch (first attempt)
- Frustrated by generic AI that doesn't capture personal voice

**Success Metrics:**

- Bot produces tweets indistinguishable from manual tweets
- Followers grow from current → 10K+ in 6 months
- Monetization opportunities emerge (sponsorships, consulting leads)
- Saves 2+ hours daily while maintaining authentic presence

### Target Audience (Who Maxime Wants to Attract)

| Segment                    | Why They Follow                                  |
| -------------------------- | ------------------------------------------------ |
| **Developers**             | Learning, tips, hot takes on tools/frameworks    |
| **Tech Recruiters**        | Talent scouting, industry insights               |
| **Crypto/SSI Enthusiasts** | Cutting-edge identity/trust technology           |
| **Young Entrepreneurs**    | Inspiration from 19yo building multiple projects |
| **French Tech Community**  | Local Bordeaux/French tech scene                 |

### User Journey

| Stage               | Experience                                           |
| ------------------- | ---------------------------------------------------- |
| **Setup**           | Configure bot with personal profile + tweet history  |
| **Daily Operation** | Bot posts 30-50 tweets/day autonomously              |
| **Human Touch**     | Maxime handles replies, DMs, engagement (30 min/day) |
| **Monitoring**      | Weekly review of performance, voice quality          |
| **Iteration**       | Refine prompts based on what performs                |

### Future Consideration

> If successful, potential open-source release for other developers facing the same time-content tradeoff.

---

## Success Metrics

### User Success Metrics

| Metric                 | Current | Target                          | Timeframe |
| ---------------------- | ------- | ------------------------------- | --------- |
| **Followers**          | 11      | 500+ verified                   | 6 months  |
| **Impressions**        | 0       | 5,000,000+                      | 6 months  |
| **Tweet Volume**       | 0       | 30-50/day automated             | Immediate |
| **Voice Authenticity** | N/A     | Pass "Could I write this?" test | Ongoing   |
| **Time Investment**    | N/A     | <30 min/day (engagement only)   | Immediate |

### Business Objectives

| Objective                 | Success Indicator                       | Timeline    |
| ------------------------- | --------------------------------------- | ----------- |
| **X Monetization Unlock** | 500 verified followers + 5M impressions | 6 months    |
| **Cost Efficiency**       | $0/month operational cost               | Ongoing     |
| **Brand Authority**       | Recognized in dev/SSI niche             | 6-12 months |
| **Lead Generation**       | First inbound opportunity               | 6 months    |

### Key Performance Indicators

| KPI                      | Measurement                     | Target       |
| ------------------------ | ------------------------------- | ------------ |
| **Daily Tweet Output**   | Automated posts/day             | 30-50        |
| **Engagement Rate**      | Likes+RTs+Replies / Impressions | >2%          |
| **Follower Growth Rate** | New followers/week              | ~20/week avg |
| **Voice Quality Score**  | Manual review (1-10)            | 8+ average   |
| **Monthly Impressions**  | X Analytics                     | ~850K/month  |

### Milestone Roadmap

| Month   | Followers | Cumulative Views | Milestone                            |
| ------- | --------- | ---------------- | ------------------------------------ |
| Month 1 | 50        | 200K             | System stable, voice refined         |
| Month 2 | 100       | 600K             | First viral tweet (10K+ impressions) |
| Month 3 | 200       | 1.5M             | Engagement patterns identified       |
| Month 4 | 300       | 2.5M             | Image tweets integrated              |
| Month 5 | 400       | 4M               | Thread strategy refined              |
| Month 6 | 500+      | 5M+              | **🎉 X Monetization Unlocked**       |

---

## MVP Scope

### Core Features (V1.0)

| Feature                     | Description                                                   | Priority |
| --------------------------- | ------------------------------------------------------------- | -------- |
| **Tweet Generation Engine** | AI generates tweets in Maxime's voice using Gemini 2.5 Flash  | P0       |
| **Twitter API Integration** | Post tweets programmatically via Twitter API v2               | P0       |
| **Personal Voice Training** | Load existing tweets + profile as context for authentic voice | P0       |
| **Trend Aggregation**       | Pull trends from Twitter + Hacker News for relevant content   | P0       |
| **Automated Scheduling**    | Post 30-50 tweets/day on configurable schedule                | P0       |
| **Rate Limiting**           | Respect Twitter API limits, prevent account suspension        | P0       |
| **Config Management**       | Easy adjustment of topics, frequency, voice parameters        | P1       |

### Tech Stack

| Component               | Technology                    | Cost      |
| ----------------------- | ----------------------------- | --------- |
| **Language**            | Python 3.11+                  | Free      |
| **AI Model**            | Gemini 2.5 Flash (Google AI)  | Free tier |
| **Twitter API**         | Twitter API v2 (Free tier)    | Free      |
| **Trend Sources**       | Twitter API + Hacker News API | Free      |
| **Scheduler**           | Python schedule / cron        | Free      |
| **Deployment (MVP)**    | Local machine                 | Free      |
| **Deployment (Future)** | VPS ($5/month)                | $5/month  |

### Out of Scope (V2.0+)

| Feature                    | Reason for Deferral                                |
| -------------------------- | -------------------------------------------------- |
| **Image Tweets**           | Adds complexity, requires image library management |
| **Thread Generation**      | More complex multi-tweet logic                     |
| **Poll Creation**          | Nice-to-have, not essential for growth             |
| **Reddit/GitHub Trending** | Additional sources can be added later              |
| **Analytics Dashboard**    | Use X Analytics directly for now                   |
| **Web UI**                 | CLI/config file is sufficient for MVP              |
| **Open-source Release**    | Focus on personal use case first                   |

### MVP Success Criteria

| Criteria               | Threshold                 | Measurement    |
| ---------------------- | ------------------------- | -------------- |
| **System Stability**   | 95% uptime, no crashes    | Error logs     |
| **Voice Authenticity** | 8/10 on manual review     | Weekly check   |
| **Tweet Volume**       | 30-50 tweets/day realized | Tweet count    |
| **No Suspensions**     | 0 account warnings        | Account health |
| **Month 1 Growth**     | 50+ followers, 200K views | X Analytics    |

### Future Vision (V2.0+)

| Feature                     | Timeline      | Impact                           |
| --------------------------- | ------------- | -------------------------------- |
| **Image Tweet Integration** | Month 2-3     | +50% engagement potential        |
| **Thread Generation**       | Month 3-4     | Deep content, authority building |
| **Multi-source Trends**     | Month 2       | Better trend coverage            |
| **Performance Dashboard**   | Month 4       | Data-driven optimization         |
| **VPS 24/7 Deployment**     | When stable   | Consistent posting               |
| **Open-source Release**     | If successful | Community, recognition           |

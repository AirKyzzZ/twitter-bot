"""CLI commands using Typer."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from twitter_bot import __version__
from twitter_bot.config import Settings, load_config
from twitter_bot.daemon import DaemonScheduler
from twitter_bot.exceptions import (
    ConfigError,
    LLMProviderError,
    SourceError,
    TwitterAPIError,
)
from twitter_bot.generation import GeminiProvider, GroqProvider, OpenAIProvider, TweetGenerator
from twitter_bot.scoring import ContentScorer
from twitter_bot.sources import RSSClient, WebExtractor, YouTubeExtractor
from twitter_bot.state import StateManager
from twitter_bot.twitter import TwitterClient

app = typer.Typer(
    name="twitter-bot",
    help="AI-powered autonomous Twitter content engine.",
    no_args_is_help=True,
)
console = Console()

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_API_ERROR = 3
EXIT_NO_CONTENT = 4


def setup_logging(verbosity: int) -> None:
    """Configure logging based on verbosity level."""
    if verbosity >= 2:
        level = logging.DEBUG
    elif verbosity >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def get_config(config_path: Path | None = None) -> Settings:
    """Load configuration with error handling."""
    try:
        return load_config(config_path)
    except ConfigError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(EXIT_CONFIG_ERROR) from None


def get_llm_provider(settings: Settings):
    """Get the LLM provider based on available API keys."""
    if settings.groq_api_key:
        return GroqProvider(settings.groq_api_key)
    elif settings.openai_api_key:
        return OpenAIProvider(settings.openai_api_key)
    elif settings.gemini_api_key:
        return GeminiProvider(settings.gemini_api_key)
    else:
        console.print(
            "[red]Error:[/red] No LLM API key configured (GROQ_API_KEY, OPENAI_API_KEY or GEMINI_API_KEY)"
        )
        raise typer.Exit(EXIT_CONFIG_ERROR)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"twitter-bot version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase verbosity (-v for INFO, -vv for DEBUG).",
    ),
) -> None:
    """Twitter Bot - AI-powered autonomous content engine."""
    setup_logging(verbose)


@app.command()
def draft(
    url: Annotated[str | None, typer.Argument(help="URL to generate tweets from")] = None,
    text: Annotated[
        str | None, typer.Option("--text", "-t", help="Text to generate tweets from")
    ] = None,
    count: Annotated[int, typer.Option("--count", "-n", help="Number of drafts")] = 3,
    config_path: Annotated[Path | None, typer.Option("--config", "-c", help="Config file")] = None,
) -> None:
    """Generate tweet drafts from a URL or text without posting."""
    settings = get_config(config_path)

    if not url and not text:
        console.print("[red]Error:[/red] Please provide either a URL or --text.")
        raise typer.Exit(EXIT_ERROR)

    source_content = ""
    # source_url = url  # Removed to fix F841

    if url:
        console.print(f"[blue]Extracting content from:[/blue] {url}")
        # Detect URL type and extract content
        try:
            if "youtube.com" in url or "youtu.be" in url:
                with YouTubeExtractor() as extractor:
                    content = extractor.extract(url)
                    source_content = f"{content.title}\n\n{content.description}"
            else:
                with WebExtractor() as extractor:
                    content = extractor.extract(url)
                    desc = content.description or ""
                    source_content = f"{content.title}\n\n{desc}\n\n{content.content}"
        except SourceError as e:
            console.print(f"[red]Failed to extract content:[/red] {e}")
            raise typer.Exit(EXIT_ERROR) from None
    else:
        source_content = text

    console.print("[blue]Generating drafts...[/blue]")

    # Get recent tweets for context
    state_manager = StateManager(settings.state_file)
    recent_tweets = [t.content for t in state_manager.get_recent_tweets(5)]

    try:
        provider = get_llm_provider(settings)
        voice_profile = None
        if settings.profile.voice_file:
            voice_path = Path(settings.profile.voice_file).expanduser()
            if voice_path.exists():
                voice_profile = voice_path.read_text()

        generator = TweetGenerator(provider, voice_profile, recent_tweets)
        drafts = generator.generate_drafts(source_content, url, n=count)
    except LLMProviderError as e:
        console.print(f"[red]LLM error:[/red] {e}")
        raise typer.Exit(EXIT_API_ERROR) from None

    console.print(f"\n[green]Generated {len(drafts)} drafts:[/green]\n")

    for i, draft_item in enumerate(drafts, 1):
        if draft_item.is_thread:
            console.print(f"[bold]Draft {i}[/bold] [cyan]THREAD ({len(draft_item.thread_parts)} parts)[/cyan]")
            for j, part in enumerate(draft_item.thread_parts, 1):
                char_count = len(part)
                color = "green" if char_count <= 280 else "red"
                console.print(f"  {j}. [{color}]{char_count}c[/{color}] {part}")
        else:
            char_count = len(draft_item.content)
            color = "green" if char_count <= 280 else "red"
            console.print(f"[bold]Draft {i}[/bold] [{color}]{char_count} chars[/{color}]")
            console.print(f"  {draft_item.content}")

        if draft_item.suggested_image:
            console.print(f"  [blue]Image suggestion:[/blue] {draft_item.suggested_image}")
        console.print()


@app.command()
def post(
    url: Annotated[str | None, typer.Argument(help="URL to generate and post tweet from")] = None,
    text: Annotated[
        str | None, typer.Option("--text", "-t", help="Text to generate and post tweet from")
    ] = None,
    image: Annotated[
        Path | None, typer.Option("--image", "-i", help="Path to image file to attach")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Generate but don't post")] = False,
    config_path: Annotated[Path | None, typer.Option("--config", "-c", help="Config file")] = None,
) -> None:
    """Generate and post a tweet from a URL or text."""
    settings = get_config(config_path)

    if not url and not text:
        console.print("[red]Error:[/red] Please provide either a URL or --text.")
        raise typer.Exit(EXIT_ERROR)

    source_content = ""
    source_url = url

    # Generate draft first
    if url:
        console.print(f"[blue]Processing:[/blue] {url}")
        try:
            if "youtube.com" in url or "youtu.be" in url:
                with YouTubeExtractor() as extractor:
                    content = extractor.extract(url)
                    source_content = f"{content.title}\n\n{content.description}"
            else:
                with WebExtractor() as extractor:
                    content = extractor.extract(url)
                    desc = content.description or ""
                    source_content = f"{content.title}\n\n{desc}\n\n{content.content}"
        except SourceError as e:
            console.print(f"[red]Failed to extract content:[/red] {e}")
            raise typer.Exit(EXIT_ERROR) from None
    else:
        source_content = text

    try:
        provider = get_llm_provider(settings)
        voice_profile = None
        if settings.profile.voice_file:
            voice_path = Path(settings.profile.voice_file).expanduser()
            if voice_path.exists():
                voice_profile = voice_path.read_text()

        generator = TweetGenerator(provider, voice_profile)
        draft = generator.generate_single(source_content, source_url)
    except LLMProviderError as e:
        console.print(f"[red]LLM error:[/red] {e}")
        raise typer.Exit(EXIT_API_ERROR) from None

    console.print("\n[green]Generated tweet:[/green]")
    console.print(f"  {draft.content}")
    console.print(f"  [dim]({len(draft.content)} characters)[/dim]\n")

    if dry_run:
        console.print("[yellow]Dry run - not posting[/yellow]")
        return

    # Post to Twitter
    try:
        with TwitterClient(
            api_key=settings.twitter.api_key,
            api_secret=settings.twitter.api_secret,
            access_token=settings.twitter.access_token,
            access_secret=settings.twitter.access_secret,
        ) as client:
            media_ids = None
            if image:
                if not image.exists():
                    console.print(f"[red]Image file not found:[/red] {image}")
                    raise typer.Exit(EXIT_ERROR)

                console.print(f"[blue]Uploading image:[/blue] {image}")
                media_id = client.upload_media(str(image))
                media_ids = [media_id]

            tweet = client.post_tweet(draft.content, media_ids=media_ids)
            console.print(f"[green]Posted![/green] Tweet ID: {tweet.id}")

            # Record in state
            state_manager = StateManager(settings.state_file)
            state_manager.record_tweet(tweet.id, draft.content, source_url)

    except TwitterAPIError as e:
        console.print(f"[red]Twitter API error:[/red] {e}")
        raise typer.Exit(EXIT_API_ERROR) from None


@app.command()
def run(
    config_path: Annotated[Path | None, typer.Option("--config", "-c", help="Config file")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Don't actually post")] = False,
    check_schedule: Annotated[
        bool, typer.Option("--check-schedule", help="Exit if not time to post based on daily limit")
    ] = False,
    images_dir: Annotated[
        Path | None, typer.Option("--images", help="Directory with images/memes to attach")
    ] = None,
) -> None:
    """Execute one autonomous cycle: fetch → score → draft → post."""
    settings = get_config(config_path)

    # Check schedule if requested
    if check_schedule:
        state_manager = StateManager(settings.state_file)
        state = state_manager.load()

        # Parse active hours
        try:
            start_str, end_str = settings.schedule.active_hours.split("-")
            start_hour = int(start_str.split(":")[0])
            end_hour = int(end_str.split(":")[0])
        except Exception:
            start_hour, end_hour = 8, 22

        current_hour = datetime.utcnow().hour  # Using UTC as per simple implementation
        # TODO: Handle timezone properly if needed using settings.schedule.timezone

        if not (start_hour <= current_hour < end_hour):
            console.print("[yellow]Outside active hours. Skipping.[/yellow]")
            return

        # Calculate interval
        active_hours_count = end_hour - start_hour
        if active_hours_count <= 0:
            active_hours_count = 14

        # Minutes available for posting
        active_minutes = active_hours_count * 60
        # Target interval in minutes
        interval_minutes = active_minutes // settings.schedule.tweets_per_day
        interval_minutes = max(10, interval_minutes)  # Minimum 10 mins

        if state.last_run:
            last_run_dt = datetime.fromisoformat(state.last_run)
            minutes_since = (datetime.utcnow() - last_run_dt).total_seconds() / 60

            if minutes_since < interval_minutes:
                console.print(
                    f"[yellow]Too soon to post.[/yellow] "
                    f"Last run: {int(minutes_since)}m ago. "
                    f"Interval: {interval_minutes}m."
                )
                return

    console.print("[blue]Starting autonomous cycle...[/blue]")

    # Fetch RSS feeds
    if not settings.sources:
        console.print("[yellow]No RSS sources configured[/yellow]")
        raise typer.Exit(EXIT_NO_CONTENT)

    feeds = [(s.url, s.weight) for s in settings.sources]

    with RSSClient() as rss:
        console.print(f"[blue]Fetching {len(feeds)} feeds...[/blue]")
        items = rss.fetch_multiple(feeds)

    if not items:
        console.print("[yellow]No items fetched from feeds[/yellow]")
        raise typer.Exit(EXIT_NO_CONTENT)

    console.print(f"[green]Fetched {len(items)} items[/green]")

    # Score and select best
    scorer = ContentScorer(
        boost_topics=settings.scoring.boost_topics,
        mute_topics=settings.scoring.mute_topics,
    )

    state_manager = StateManager(settings.state_file)
    state = state_manager.load()

    scorable = [(item.title, item.url, item.summary, weight) for item, weight in items]

    best = scorer.select_best(scorable, state.processed_urls)

    if not best:
        console.print("[yellow]No suitable content found after filtering[/yellow]")
        raise typer.Exit(EXIT_NO_CONTENT)

    console.print(f"[green]Selected:[/green] {best.title[:60]}...")
    console.print(f"  Score: {best.score:.2f}, Topics: {best.matched_boost_topics}")

    # Get recent tweets for context (to avoid repetition)
    recent_tweets = [t.content for t in state_manager.get_recent_tweets(5)]

    # Generate tweet
    try:
        provider = get_llm_provider(settings)
        voice_profile = None
        if settings.profile.voice_file:
            voice_path = Path(settings.profile.voice_file).expanduser()
            if voice_path.exists():
                voice_profile = voice_path.read_text()

        generator = TweetGenerator(provider, voice_profile, recent_tweets)
        draft = generator.generate_single(best.content, best.url)
    except LLMProviderError as e:
        console.print(f"[red]LLM error:[/red] {e}")
        raise typer.Exit(EXIT_API_ERROR) from None

    # Display generated content
    if draft.is_thread:
        console.print(f"\n[green]Generated thread ({len(draft.thread_parts)} tweets):[/green]")
        for i, part in enumerate(draft.thread_parts, 1):
            console.print(f"  {i}. {part}")
    else:
        console.print(f"\n[green]Generated:[/green] {draft.content}")

    if draft.suggested_image:
        console.print(f"[blue]Suggested image:[/blue] {draft.suggested_image}")

    if dry_run:
        console.print("\n[yellow]Dry run - not posting[/yellow]")
        state_manager.mark_url_processed(best.url)
        return

    # Handle image attachment
    media_ids = None
    if images_dir and images_dir.exists() and draft.suggested_image:
        # Try to find a matching image from the directory
        import random

        image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
        if image_files:
            # For now, randomly select an image when one is suggested
            # Future: could use AI to match suggestion to available images
            selected_image = random.choice(image_files)
            console.print(f"[blue]Attaching image:[/blue] {selected_image.name}")

    # Post
    try:
        with TwitterClient(
            api_key=settings.twitter.api_key,
            api_secret=settings.twitter.api_secret,
            access_token=settings.twitter.access_token,
            access_secret=settings.twitter.access_secret,
        ) as client:
            # Upload image if we have one
            if media_ids is None and images_dir and images_dir.exists() and draft.suggested_image:
                import random

                image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
                if image_files:
                    selected_image = random.choice(image_files)
                    try:
                        media_id = client.upload_media(str(selected_image))
                        media_ids = [media_id]
                        console.print(f"[green]Uploaded image:[/green] {selected_image.name}")
                    except TwitterAPIError as e:
                        console.print(f"[yellow]Failed to upload image:[/yellow] {e}")

            if draft.is_thread and len(draft.thread_parts) > 1:
                # Post as thread
                tweets = client.post_thread(draft.thread_parts, media_ids_first=media_ids)
                console.print(f"\n[green]Posted thread![/green] {len(tweets)} tweets")
                console.print(f"  First tweet ID: {tweets[0].id}")
                # Record the first tweet in the thread
                state_manager.record_tweet(
                    tweets[0].id,
                    " | ".join(draft.thread_parts),  # Store full thread content
                    best.url,
                )
            else:
                # Post single tweet
                tweet = client.post_tweet(draft.content, media_ids=media_ids)
                console.print(f"\n[green]Posted![/green] Tweet ID: {tweet.id}")
                state_manager.record_tweet(tweet.id, draft.content, best.url)

    except TwitterAPIError as e:
        console.print(f"[red]Twitter API error:[/red] {e}")
        raise typer.Exit(EXIT_API_ERROR) from None

    state_manager.update_last_run()
    console.print("[green]Cycle complete![/green]")


@app.command()
def daemon(
    config_path: Annotated[Path | None, typer.Option("--config", "-c", help="Config file")] = None,
    images_dir: Annotated[
        Path | None, typer.Option("--images", help="Directory with images/memes to attach")
    ] = None,
) -> None:
    """Start continuous autonomous mode (24/7 operation)."""
    settings = get_config(config_path)

    console.print("[blue]Starting daemon mode...[/blue]")
    console.print(f"  Tweets/day: {settings.schedule.tweets_per_day}")
    console.print(f"  Active hours: {settings.schedule.active_hours}")
    console.print(f"  Timezone: {settings.schedule.timezone}")
    if images_dir:
        console.print(f"  Images dir: {images_dir}")
    console.print("\n[dim]Press Ctrl+C to stop[/dim]\n")

    def run_cycle() -> None:
        """Run a single posting cycle."""
        import random

        # This calls the same logic as the 'run' command
        try:
            # Inline the run logic here for the daemon
            if not settings.sources:
                return

            feeds = [(s.url, s.weight) for s in settings.sources]

            with RSSClient() as rss:
                items = rss.fetch_multiple(feeds)

            if not items:
                return

            scorer = ContentScorer(
                boost_topics=settings.scoring.boost_topics,
                mute_topics=settings.scoring.mute_topics,
            )

            state_manager = StateManager(settings.state_file)
            state = state_manager.load()

            scorable = [(item.title, item.url, item.summary, weight) for item, weight in items]

            best = scorer.select_best(scorable, state.processed_urls)
            if not best:
                return

            # Get recent tweets for context (to avoid repetition)
            recent_tweets = [t.content for t in state_manager.get_recent_tweets(5)]

            provider = get_llm_provider(settings)
            voice_profile = None
            if settings.profile.voice_file:
                voice_path = Path(settings.profile.voice_file).expanduser()
                if voice_path.exists():
                    voice_profile = voice_path.read_text()

            generator = TweetGenerator(provider, voice_profile, recent_tweets)
            draft = generator.generate_single(best.content, best.url)

            with TwitterClient(
                api_key=settings.twitter.api_key,
                api_secret=settings.twitter.api_secret,
                access_token=settings.twitter.access_token,
                access_secret=settings.twitter.access_secret,
            ) as client:
                # Handle image attachment
                media_ids = None
                if images_dir and images_dir.exists() and draft.suggested_image:
                    image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
                    if image_files:
                        selected_image = random.choice(image_files)
                        try:
                            media_id = client.upload_media(str(selected_image))
                            media_ids = [media_id]
                            logging.info(f"Uploaded image: {selected_image.name}")
                        except TwitterAPIError as e:
                            logging.warning(f"Failed to upload image: {e}")

                if draft.is_thread and len(draft.thread_parts) > 1:
                    # Post as thread
                    tweets = client.post_thread(draft.thread_parts, media_ids_first=media_ids)
                    logging.info(f"Posted thread with {len(tweets)} tweets")
                    state_manager.record_tweet(
                        tweets[0].id,
                        " | ".join(draft.thread_parts),
                        best.url,
                    )
                else:
                    # Post single tweet
                    tweet = client.post_tweet(draft.content, media_ids=media_ids)
                    logging.info(f"Posted tweet: {tweet.id}")
                    state_manager.record_tweet(tweet.id, draft.content, best.url)

            state_manager.update_last_run()

        except Exception as e:
            logging.error(f"Cycle error: {e}")

    scheduler = DaemonScheduler(
        run_cycle=run_cycle,
        tweets_per_day=settings.schedule.tweets_per_day,
        active_hours=settings.schedule.active_hours,
        timezone=settings.schedule.timezone,
    )

    scheduler.run_forever()


@app.command()
def tune(
    boost: Annotated[
        list[str] | None, typer.Option("--boost", "-b", help="Topics to boost")
    ] = None,
    mute: Annotated[list[str] | None, typer.Option("--mute", "-m", help="Topics to mute")] = None,
    config_path: Annotated[Path | None, typer.Option("--config", "-c", help="Config file")] = None,
) -> None:
    """Adjust scoring weights for topics."""
    settings = get_config(config_path)

    if boost:
        current = set(settings.scoring.boost_topics)
        current.update(boost)
        console.print(f"[green]Boosted topics:[/green] {', '.join(current)}")

    if mute:
        current = set(settings.scoring.mute_topics)
        current.update(mute)
        console.print(f"[red]Muted topics:[/red] {', '.join(current)}")

    console.print("\n[yellow]Note:[/yellow] Changes are in-memory only.")
    console.print("To persist, update your config.yaml file.")


@app.command()
def status(
    config_path: Annotated[Path | None, typer.Option("--config", "-c", help="Config file")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Show configuration, queue status, and health check."""
    settings = get_config(config_path)

    state_manager = StateManager(settings.state_file)
    state = state_manager.load()
    recent = state_manager.get_recent_tweets(5)

    if json_output:
        import json

        data = {
            "config": {
                "tweets_per_day": settings.schedule.tweets_per_day,
                "active_hours": settings.schedule.active_hours,
                "sources_count": len(settings.sources),
                "boost_topics": settings.scoring.boost_topics,
                "mute_topics": settings.scoring.mute_topics,
            },
            "state": {
                "total_posted": len(state.posted_tweets),
                "urls_processed": len(state.processed_urls),
                "last_run": state.last_run,
            },
            "health": {
                "config_valid": True,
                "groq_configured": bool(settings.groq_api_key),
                "openai_configured": bool(settings.openai_api_key),
                "gemini_configured": bool(settings.gemini_api_key),
                "twitter_configured": bool(settings.twitter.api_key),
            },
        }
        console.print(json.dumps(data, indent=2))
        return

    # Rich formatted output
    console.print("\n[bold]Twitter Bot Status[/bold]\n")

    # Config table
    config_table = Table(title="Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value")

    config_table.add_row("Tweets/day", str(settings.schedule.tweets_per_day))
    config_table.add_row("Active hours", settings.schedule.active_hours)
    config_table.add_row("Timezone", settings.schedule.timezone)
    config_table.add_row("RSS sources", str(len(settings.sources)))
    config_table.add_row("Boost topics", ", ".join(settings.scoring.boost_topics) or "None")
    config_table.add_row("Mute topics", ", ".join(settings.scoring.mute_topics) or "None")

    console.print(config_table)

    # State table
    state_table = Table(title="\nState")
    state_table.add_column("Metric", style="cyan")
    state_table.add_column("Value")

    state_table.add_row("Total posted", str(len(state.posted_tweets)))
    state_table.add_row("URLs processed", str(len(state.processed_urls)))
    state_table.add_row("Last run", state.last_run or "Never")

    console.print(state_table)

    # Health checks
    console.print("\n[bold]Health Checks[/bold]")
    console.print("  Config valid: [green]✓[/green]")
    groq_status = (
        "[green]✓ Configured (FREE)[/green]" if settings.groq_api_key else "[dim]✗ Not configured[/dim]"
    )
    console.print(f"  Groq API: {groq_status}")
    openai_status = (
        "[green]✓ Configured[/green]" if settings.openai_api_key else "[dim]✗ Not configured[/dim]"
    )
    console.print(f"  OpenAI API: {openai_status}")
    gemini_status = (
        "[green]✓ Configured[/green]" if settings.gemini_api_key else "[dim]✗ Not configured[/dim]"
    )
    console.print(f"  Gemini API: {gemini_status}")
    twitter_status = (
        "[green]✓ Configured[/green]" if settings.twitter.api_key else "[red]✗ Not configured[/red]"
    )
    console.print(f"  Twitter API: {twitter_status}")

    # Recent tweets
    if recent:
        console.print("\n[bold]Recent Tweets[/bold]")
        for tweet in recent[-3:]:
            console.print(f"  • {tweet.content[:60]}...")


@app.command(name="dry-run")
def dry_run_cmd(
    count: Annotated[int, typer.Option("--count", "-n", help="Number of tweets to preview")] = 5,
    config_path: Annotated[Path | None, typer.Option("--config", "-c", help="Config file")] = None,
) -> None:
    """Preview next N planned tweets without posting."""
    settings = get_config(config_path)

    console.print(f"[blue]Previewing next {count} planned tweets...[/blue]\n")

    if not settings.sources:
        console.print("[yellow]No RSS sources configured[/yellow]")
        raise typer.Exit(EXIT_NO_CONTENT)

    feeds = [(s.url, s.weight) for s in settings.sources]

    with RSSClient() as rss:
        items = rss.fetch_multiple(feeds)

    if not items:
        console.print("[yellow]No items fetched[/yellow]")
        raise typer.Exit(EXIT_NO_CONTENT)

    scorer = ContentScorer(
        boost_topics=settings.scoring.boost_topics,
        mute_topics=settings.scoring.mute_topics,
    )

    state_manager = StateManager(settings.state_file)
    state = state_manager.load()

    scorable = [(item.title, item.url, item.summary, weight) for item, weight in items]

    scored = scorer.score_and_filter(scorable)
    unprocessed = [s for s in scored if s.url not in state.processed_urls][:count]

    if not unprocessed:
        console.print("[yellow]No unprocessed content available[/yellow]")
        raise typer.Exit(EXIT_NO_CONTENT)

    table = Table(title=f"Next {len(unprocessed)} Planned Tweets")
    table.add_column("#", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Title")
    table.add_column("Topics")

    for i, item in enumerate(unprocessed, 1):
        table.add_row(
            str(i),
            f"{item.score:.2f}",
            item.title[:50] + "..." if len(item.title) > 50 else item.title,
            ", ".join(item.matched_boost_topics) or "-",
        )

    console.print(table)


if __name__ == "__main__":
    app()

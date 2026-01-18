"""CLI commands using Typer."""

import logging
from datetime import UTC, datetime
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
from twitter_bot.generation import (
    FallbackProvider,
    GeminiProvider,
    GroqProvider,
    OpenAIProvider,
    TweetGenerator,
)
from twitter_bot.sources import WebExtractor, YouTubeExtractor
from twitter_bot.state import StateManager
from twitter_bot.state.manager import RepliedTweet
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


def is_rate_limit_error(error: Exception) -> bool:
    """Check if error is a rate limit (should exit gracefully)."""
    error_str = str(error).lower()
    return any(x in error_str for x in ["rate limit", "rate_limit", "429", "quota", "too many"])


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
    """Get the LLM provider with automatic fallback on rate limits.

    Priority: Gemini (generous free tier) -> Groq (fast) -> OpenAI (paid fallback)
    """
    providers: list[tuple[str, object]] = []

    if settings.gemini_api_key:
        providers.append(("Gemini", GeminiProvider(settings.gemini_api_key)))
    if settings.groq_api_key:
        providers.append(("Groq", GroqProvider(settings.groq_api_key)))
    if settings.openai_api_key:
        providers.append(("OpenAI", OpenAIProvider(settings.openai_api_key)))

    if not providers:
        console.print(
            "[red]Error:[/red] No LLM API key configured "
            "(GROQ_API_KEY, GEMINI_API_KEY or OPENAI_API_KEY)"
        )
        raise typer.Exit(EXIT_CONFIG_ERROR)

    # Single provider - use directly
    if len(providers) == 1:
        return providers[0][1]

    # Multiple providers - use fallback chain
    console.print(
        f"[dim]LLM fallback chain: {' -> '.join(name for name, _ in providers)}[/dim]"
    )
    return FallbackProvider(providers)


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
    recent_tweets = [t.content for t in state_manager.get_recent_tweets(10)]

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
        if is_rate_limit_error(e):
            console.print(f"[yellow]Rate limited, try again later:[/yellow] {e}")
            raise typer.Exit(EXIT_SUCCESS) from None
        console.print(f"[red]LLM error:[/red] {e}")
        raise typer.Exit(EXIT_API_ERROR) from None

    console.print(f"\n[green]Generated {len(drafts)} drafts:[/green]\n")

    for i, draft_item in enumerate(drafts, 1):
        if draft_item.is_thread:
            console.print(
                f"[bold]Draft {i}[/bold] [cyan]THREAD ({len(draft_item.thread_parts)} parts)[/cyan]"
            )
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

        # Get recent tweets for context
        state_manager = StateManager(settings.state_file)
        recent_tweets = [t.content for t in state_manager.get_recent_tweets(10)]

        generator = TweetGenerator(provider, voice_profile, recent_tweets)
        draft = generator.generate_single(source_content, source_url)
    except LLMProviderError as e:
        if is_rate_limit_error(e):
            console.print(f"[yellow]Rate limited, try again later:[/yellow] {e}")
            raise typer.Exit(EXIT_SUCCESS) from None
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
        if e.status_code == 429:
            console.print("[yellow]Rate limit hit - exiting silently[/yellow]")
            raise typer.Exit(EXIT_SUCCESS) from None
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
        from zoneinfo import ZoneInfo

        state_manager = StateManager(settings.state_file)
        state = state_manager.load()

        # Parse active hours
        try:
            start_str, end_str = settings.schedule.active_hours.split("-")
            start_hour = int(start_str.split(":")[0])
            end_hour = int(end_str.split(":")[0])
        except Exception:
            start_hour, end_hour = 8, 22

        # Convert current UTC time to configured timezone
        tz = ZoneInfo(settings.schedule.timezone)
        current_hour = datetime.now(tz).hour

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
            if last_run_dt.tzinfo is None:
                last_run_dt = last_run_dt.replace(tzinfo=UTC)
            minutes_since = (datetime.now(UTC) - last_run_dt).total_seconds() / 60

            if minutes_since < interval_minutes:
                console.print(
                    f"[yellow]Too soon to post.[/yellow] "
                    f"Last run: {int(minutes_since)}m ago. "
                    f"Interval: {interval_minutes}m."
                )
                return

    console.print("[blue]Starting autonomous cycle...[/blue]")

    # Check poster daily limit
    state_manager = StateManager(settings.state_file)
    state = state_manager.load()

    # Count today's posts
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(settings.schedule.timezone)
    today_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)

    posts_today = 0
    for tweet in state.posted_tweets:
        try:
            posted_at = datetime.fromisoformat(tweet.posted_at)
            if posted_at.tzinfo is None:

                posted_at = posted_at.replace(tzinfo=UTC)
            if posted_at.astimezone(tz) >= today_start:
                posts_today += 1
        except Exception:
            continue

    if posts_today >= settings.poster.max_per_day:
        console.print(
            f"[yellow]Poster daily limit reached "
            f"({posts_today}/{settings.poster.max_per_day})[/yellow]"
        )
        console.print("Skipping post cycle. Reply bot can still post.")
        return

    console.print(f"[dim]Posts today: {posts_today}/{settings.poster.max_per_day}[/dim]")

    # Topic-based Generation (Generalist Mode)
    if not settings.scoring.boost_topics:
        console.print("[red]Error:[/red] No boost_topics configured in config.yaml")
        raise typer.Exit(EXIT_CONFIG_ERROR)

    # Select topic with rotation (avoid recently used topics)
    topic = state_manager.select_topic_with_rotation(settings.scoring.boost_topics)
    console.print(f"[green]Selected Topic:[/green] {topic}")

    # Get recent tweets for context - use more for better deduplication
    recent_tweets = [t.content for t in state_manager.get_recent_tweets(15)]

    # Generate tweet
    try:
        provider = get_llm_provider(settings)
        voice_profile = None
        if settings.profile.voice_file:
            voice_path = Path(settings.profile.voice_file).expanduser()
            if voice_path.exists():
                voice_profile = voice_path.read_text()

        generator = TweetGenerator(provider, voice_profile, recent_tweets)
        draft = generator.generate_from_topic(topic)
    except LLMProviderError as e:
        if is_rate_limit_error(e):
            console.print(f"[yellow]Rate limited, skipping this cycle:[/yellow] {e}")
            raise typer.Exit(EXIT_SUCCESS) from None
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
        return

    # Handle image attachment - select image once before posting
    media_ids = None
    selected_image = None
    if images_dir and images_dir.exists() and draft.suggested_image:
        import random as rnd

        # Try to find a matching image from the directory
        image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
        if image_files:
            # For now, randomly select an image when one is suggested
            # Future: could use AI to match suggestion to available images
            selected_image = rnd.choice(image_files)
            console.print(f"[blue]Attaching image:[/blue] {selected_image.name}")

    # Post
    try:
        with TwitterClient(
            api_key=settings.twitter.api_key,
            api_secret=settings.twitter.api_secret,
            access_token=settings.twitter.access_token,
            access_secret=settings.twitter.access_secret,
        ) as client:
            # Upload the selected image
            if selected_image:
                try:
                    media_id = client.upload_media(str(selected_image))
                    media_ids = [media_id]
                    console.print(f"[green]Uploaded image:[/green] {selected_image.name}")
                except TwitterAPIError as e:
                    console.print(f"[yellow]Failed to upload image:[/yellow] {e}")

            # Check if threads are allowed
            if draft.is_thread and len(draft.thread_parts) > 1 and settings.poster.allow_threads:
                # Post as thread
                tweets = client.post_thread(draft.thread_parts, media_ids_first=media_ids)
                console.print(f"\n[green]Posted thread![/green] {len(tweets)} tweets")
                console.print(f"  First tweet ID: {tweets[0].id}")
                # Record the first tweet in the thread
                state_manager.record_tweet(
                    tweets[0].id,
                    " | ".join(draft.thread_parts),  # Store full thread content
                    None,  # No source URL
                    source_title=f"Topic: {topic}",
                )
            else:
                # Post single tweet (or first part if threads disabled)
                content_to_post = draft.content
                if draft.is_thread and draft.thread_parts and not settings.poster.allow_threads:
                    content_to_post = draft.thread_parts[0]
                    console.print(
                        "[yellow]Threads disabled - posting first part only[/yellow]"
                    )

                tweet = client.post_tweet(content_to_post, media_ids=media_ids)
                console.print(f"\n[green]Posted![/green] Tweet ID: {tweet.id}")
                state_manager.record_tweet(
                    tweet.id,
                    content_to_post,
                    None,  # No source URL
                    source_title=f"Topic: {topic}",
                )

            # Record topic for rotation tracking
            state_manager.record_topic(topic)

    except TwitterAPIError as e:
        console.print(f"[red]Twitter API error:[/red] {e}")
        if e.status_code == 429:
            console.print("[yellow]Rate limit hit - exiting silently[/yellow]")
            raise typer.Exit(EXIT_SUCCESS) from None
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
        from zoneinfo import ZoneInfo

        # Topic-based Generation (Generalist Mode)
        try:
            if not settings.scoring.boost_topics:
                logging.error("No boost_topics configured")
                return

            state_manager = StateManager(settings.state_file)
            state = state_manager.load()  # Load latest state

            # Check poster daily limit
            tz = ZoneInfo(settings.schedule.timezone)
            today_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)

            posts_today = 0
            for tweet in state.posted_tweets:
                try:
                    posted_at = datetime.fromisoformat(tweet.posted_at)
                    if posted_at.tzinfo is None:
                        posted_at = posted_at.replace(tzinfo=UTC)
                    if posted_at.astimezone(tz) >= today_start:
                        posts_today += 1
                except Exception:
                    continue

            if posts_today >= settings.poster.max_per_day:
                logging.info(
                    f"Poster daily limit reached ({posts_today}/{settings.poster.max_per_day})"
                )
                return

            # Select topic with rotation (avoid recently used topics)
            topic = state_manager.select_topic_with_rotation(settings.scoring.boost_topics)
            logging.info(f"Selected Topic: {topic}")

            # Get recent tweets for context - use more for better deduplication
            recent_tweets = [t.content for t in state_manager.get_recent_tweets(15)]

            provider = get_llm_provider(settings)
            voice_profile = None
            if settings.profile.voice_file:
                voice_path = Path(settings.profile.voice_file).expanduser()
                if voice_path.exists():
                    voice_profile = voice_path.read_text()

            generator = TweetGenerator(provider, voice_profile, recent_tweets)
            draft = generator.generate_from_topic(topic)

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

                allow_threads = settings.poster.allow_threads
                if draft.is_thread and len(draft.thread_parts) > 1 and allow_threads:
                    # Post as thread
                    tweets = client.post_thread(draft.thread_parts, media_ids_first=media_ids)
                    logging.info(f"Posted thread with {len(tweets)} tweets")
                    state_manager.record_tweet(
                        tweets[0].id,
                        " | ".join(draft.thread_parts),
                        None,  # No source URL
                        source_title=f"Topic: {topic}",
                    )
                else:
                    # Post single tweet (or first part if threads disabled)
                    content_to_post = draft.content
                    if draft.is_thread and draft.thread_parts and not settings.poster.allow_threads:
                        content_to_post = draft.thread_parts[0]
                        logging.info("Threads disabled - posting first part only")

                    tweet = client.post_tweet(content_to_post, media_ids=media_ids)
                    logging.info(f"Posted tweet: {tweet.id}")
                    state_manager.record_tweet(
                        tweet.id,
                        content_to_post,
                        None,  # No source URL
                        source_title=f"Topic: {topic}",
                    )

                # Record topic for rotation tracking
                state_manager.record_topic(topic)

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
        "[green]✓ Configured (FREE)[/green]"
        if settings.groq_api_key
        else "[dim]✗ Not configured[/dim]"
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

    if not settings.scoring.boost_topics:
        console.print("[red]Error:[/red] No boost_topics configured")
        raise typer.Exit(EXIT_CONFIG_ERROR)

    # Initialize generator
    state_manager = StateManager(settings.state_file)
    recent_tweets = [t.content for t in state_manager.get_recent_tweets(10)]

    try:
        provider = get_llm_provider(settings)
        voice_profile = None
        if settings.profile.voice_file:
            voice_path = Path(settings.profile.voice_file).expanduser()
            if voice_path.exists():
                voice_profile = voice_path.read_text()

        generator = TweetGenerator(provider, voice_profile, recent_tweets)
    except LLMProviderError as e:
        if is_rate_limit_error(e):
            console.print(f"[yellow]Rate limited, try again later:[/yellow] {e}")
            raise typer.Exit(EXIT_SUCCESS) from None
        console.print(f"[red]LLM error:[/red] {e}")
        raise typer.Exit(EXIT_API_ERROR) from None

    import random

    for i in range(count):
        topic = random.choice(settings.scoring.boost_topics)
        console.print(f"[bold cyan]Draft {i + 1}/{count} - Topic: {topic}[/bold cyan]")

        draft = generator.generate_from_topic(topic)

        if draft.is_thread:
            console.print(f"[green]Thread ({len(draft.thread_parts)} tweets):[/green]")
            for j, part in enumerate(draft.thread_parts, 1):
                console.print(f"  {j}. {part}")
        else:
            console.print(f"[green]Tweet:[/green] {draft.content}")

        if draft.suggested_image:
            console.print(f"[blue]Image suggestion:[/blue] {draft.suggested_image}")

        console.print()


# ============================================================================
# REPLY BOT COMMANDS
# ============================================================================


@app.command(name="reply-watch")
def reply_watch(
    headless: Annotated[
        bool, typer.Option("--headless", help="Run browser in headless mode")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Generate replies but don't post")
    ] = False,
    config_path: Annotated[
        Path | None, typer.Option("--config", "-c", help="Config file")
    ] = None,
) -> None:
    """Watch timeline and reply to high-scoring tweets (local daemon)."""
    import asyncio

    settings = get_config(config_path)

    if not settings.reply.enabled:
        console.print("[yellow]Reply bot is disabled in config[/yellow]")
        console.print("Set 'reply.enabled: true' in config.yaml to enable.")
        return

    console.print("[blue]Starting reply watcher...[/blue]")
    console.print(f"  Max replies/day: {settings.reply.max_per_day}")
    console.print(f"  Score threshold: {settings.reply.score_threshold}")
    console.print(f"  Watch interval: {settings.reply.watch_interval_seconds}s")
    console.print(f"  Min delay between replies: {settings.reply.min_delay_seconds}s")
    console.print(f"  Headless: {headless}")
    console.print(f"  Dry run: {dry_run}")
    console.print("\n[dim]Press Ctrl+C to stop[/dim]\n")

    asyncio.run(_watch_and_reply(settings, headless, dry_run))


async def _watch_and_reply(settings: Settings, headless: bool, dry_run: bool) -> None:
    """Async watch loop for reply bot."""
    from twitter_bot.browser import BrowserReplyPoster, StealthBrowser, TimelineWatcher
    from twitter_bot.reply import ReplyGenerator, TweetScorer

    state_manager = StateManager(settings.state_file)
    scorer = TweetScorer(settings.reply, settings.scoring.boost_topics, state_manager)

    # Set up LLM provider and generator
    provider = get_llm_provider(settings)
    voice_profile = ""
    if settings.profile.voice_file:
        voice_path = Path(settings.profile.voice_file).expanduser()
        if voice_path.exists():
            voice_profile = voice_path.read_text()

    generator = ReplyGenerator(provider, voice_profile, state_manager)
    cookies_path = Path(settings.reply.cookies_path).expanduser()

    async with StealthBrowser(cookies_path, headless=headless) as browser:
        # Ensure logged in
        if not await browser.ensure_logged_in():
            console.print("[red]Could not log in to Twitter[/red]")
            return

        console.print("[green]Logged in! Starting watch...[/green]")

        watcher = TimelineWatcher(browser, state_manager)

        async def on_new_tweets(tweets) -> None:
            """Handle new tweets from timeline."""
            # Check daily limit
            today_count = state_manager.get_replies_today_count(settings.schedule.timezone)
            if today_count >= settings.reply.max_per_day:
                max_day = settings.reply.max_per_day
                console.print(
                    f"[yellow]Daily limit reached ({today_count}/{max_day})[/yellow]"
                )
                return

            # Check delay since last reply
            if not state_manager.can_reply_now(settings.reply.min_delay_seconds):
                console.print("[dim]Too soon since last reply, waiting...[/dim]")
                return

            # Score and filter tweets
            ranked = scorer.filter_and_rank(tweets)
            if not ranked:
                console.print("[dim]No tweets passed scoring threshold[/dim]")
                return

            # Take best tweet
            best_tweet, score = ranked[0]
            console.print(f"\n[cyan]Found candidate (score: {score:.2f}):[/cyan]")
            console.print(f"  @{best_tweet.author_handle}: {best_tweet.content[:80]}...")

            # Generate reply
            reply_text, reply_type = generator.generate_reply(best_tweet)
            console.print(f"[green]Generated ({reply_type}):[/green] {reply_text}")

            if dry_run:
                console.print("[yellow]DRY RUN - not posting[/yellow]")
                return

            # Determine posting method (browser vs API)
            use_browser = state_manager.should_use_browser(
                settings.reply.browser_post_ratio
            )
            posting_method = "browser" if use_browser else "api"
            console.print(f"[dim]Posting via: {posting_method}[/dim]")

            reply_tweet_id: str | None = None

            if use_browser:
                # Try browser posting first
                poster = BrowserReplyPoster(browser)
                success, error = await poster.post_reply(best_tweet, reply_text)

                if success:
                    console.print("[green]Posted via browser![/green]")
                    reply_tweet_id = "browser-posted"  # Browser doesn't return ID
                    await poster.return_to_timeline()
                else:
                    console.print(f"[yellow]Browser post failed: {error}[/yellow]")
                    if settings.reply.fallback_to_api:
                        console.print("[dim]Falling back to API...[/dim]")
                        use_browser = False
                        posting_method = "api"
                    else:
                        console.print("[red]Fallback disabled, skipping[/red]")
                        return

            if not use_browser:
                # Post via API
                try:
                    with TwitterClient(
                        api_key=settings.twitter.api_key,
                        api_secret=settings.twitter.api_secret,
                        access_token=settings.twitter.access_token,
                        access_secret=settings.twitter.access_secret,
                    ) as client:
                        result = client.post_reply(reply_text, best_tweet.tweet_id)
                        console.print(f"[green]Posted![/green] Tweet ID: {result.id}")
                        reply_tweet_id = result.id

                except TwitterAPIError as e:
                    console.print(f"[red]Failed to post reply:[/red] {e}")
                    return

            # Record the reply if successful
            if reply_tweet_id:
                state_manager.record_reply(
                    RepliedTweet(
                        original_tweet_id=best_tweet.tweet_id,
                        original_author=best_tweet.author_handle,
                        original_content=best_tweet.content[:500],
                        reply_tweet_id=reply_tweet_id,
                        reply_content=reply_text,
                        reply_type=reply_type,
                        replied_at=datetime.now(UTC).isoformat(),
                        posting_method=posting_method,
                    )
                )
                state_manager.record_posting_method(posting_method)

        # Start watching
        await watcher.watch(
            interval=settings.reply.watch_interval_seconds,
            on_new_tweets=on_new_tweets,
        )


@app.command(name="reply-once")
def reply_once(
    headless: Annotated[
        bool, typer.Option("--headless", help="Run browser in headless mode")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Generate reply but don't post")
    ] = False,
    config_path: Annotated[
        Path | None, typer.Option("--config", "-c", help="Config file")
    ] = None,
) -> None:
    """Scrape timeline once, generate and post one reply, then exit."""
    import asyncio

    settings = get_config(config_path)

    if not settings.reply.enabled:
        console.print("[yellow]Reply bot is disabled in config[/yellow]")
        return

    console.print("[blue]Running single reply cycle...[/blue]")
    asyncio.run(_reply_once(settings, headless, dry_run))


async def _reply_once(settings: Settings, headless: bool, dry_run: bool) -> None:
    """Single reply cycle."""
    from twitter_bot.browser import BrowserReplyPoster, StealthBrowser, TimelineWatcher
    from twitter_bot.reply import ReplyGenerator, TweetScorer

    state_manager = StateManager(settings.state_file)
    scorer = TweetScorer(settings.reply, settings.scoring.boost_topics, state_manager)

    provider = get_llm_provider(settings)
    voice_profile = ""
    if settings.profile.voice_file:
        voice_path = Path(settings.profile.voice_file).expanduser()
        if voice_path.exists():
            voice_profile = voice_path.read_text()

    generator = ReplyGenerator(provider, voice_profile, state_manager)
    cookies_path = Path(settings.reply.cookies_path).expanduser()

    async with StealthBrowser(cookies_path, headless=headless) as browser:
        if not await browser.ensure_logged_in():
            console.print("[red]Could not log in to Twitter[/red]")
            return

        console.print("[green]Logged in! Scraping timeline...[/green]")

        watcher = TimelineWatcher(browser, state_manager)
        tweets = await watcher.scrape_once()

        if not tweets:
            console.print("[yellow]No tweets found on timeline[/yellow]")
            return

        console.print(f"[blue]Found {len(tweets)} tweets[/blue]")

        # Score and filter
        ranked = scorer.filter_and_rank(tweets)

        if not ranked:
            console.print("[yellow]No tweets passed scoring threshold[/yellow]")
            console.print("\nTop 3 tweets by score (below threshold):")
            all_scored = [(t, scorer.score(t)) for t in tweets]
            all_scored.sort(key=lambda x: x[1], reverse=True)
            for tweet, score in all_scored[:3]:
                console.print(f"  [{score:.2f}] @{tweet.author_handle}: {tweet.content[:60]}...")
            return

        console.print(f"[green]{len(ranked)} tweets passed threshold[/green]")

        # Show top candidates
        console.print("\n[bold]Top candidates:[/bold]")
        for tweet, score in ranked[:5]:
            console.print(f"  [{score:.2f}] @{tweet.author_handle}: {tweet.content[:60]}...")

        # Generate reply for best tweet
        best_tweet, score = ranked[0]
        console.print(f"\n[cyan]Selected (score: {score:.2f}):[/cyan]")
        console.print(f"  @{best_tweet.author_handle}")
        console.print(f"  {best_tweet.content}")

        reply_text, reply_type = generator.generate_reply(best_tweet)
        console.print(f"\n[green]Generated ({reply_type}):[/green]")
        console.print(f"  {reply_text}")
        console.print(f"  [dim]({len(reply_text)} chars)[/dim]")

        if dry_run:
            console.print("\n[yellow]DRY RUN - not posting[/yellow]")
            return

        # Confirm before posting
        if not typer.confirm("\nPost this reply?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

        # Determine posting method (browser vs API)
        use_browser = state_manager.should_use_browser(
            settings.reply.browser_post_ratio
        )
        posting_method = "browser" if use_browser else "api"
        console.print(f"[dim]Posting via: {posting_method}[/dim]")

        reply_tweet_id: str | None = None

        if use_browser:
            # Try browser posting first
            poster = BrowserReplyPoster(browser)
            success, error = await poster.post_reply(best_tweet, reply_text)

            if success:
                console.print("\n[green]Posted via browser![/green]")
                reply_tweet_id = "browser-posted"
                await poster.return_to_timeline()
            else:
                console.print(f"[yellow]Browser post failed: {error}[/yellow]")
                if settings.reply.fallback_to_api:
                    console.print("[dim]Falling back to API...[/dim]")
                    use_browser = False
                    posting_method = "api"
                else:
                    console.print("[red]Fallback disabled, aborting[/red]")
                    return

        if not use_browser:
            # Post via API
            try:
                with TwitterClient(
                    api_key=settings.twitter.api_key,
                    api_secret=settings.twitter.api_secret,
                    access_token=settings.twitter.access_token,
                    access_secret=settings.twitter.access_secret,
                ) as client:
                    result = client.post_reply(reply_text, best_tweet.tweet_id)
                    console.print(f"\n[green]Posted![/green] Tweet ID: {result.id}")
                    reply_tweet_id = result.id

            except TwitterAPIError as e:
                console.print(f"[red]Failed to post:[/red] {e}")
                raise typer.Exit(EXIT_API_ERROR) from None

        # Record the reply if successful
        if reply_tweet_id:
            state_manager.record_reply(
                RepliedTweet(
                    original_tweet_id=best_tweet.tweet_id,
                    original_author=best_tweet.author_handle,
                    original_content=best_tweet.content[:500],
                    reply_tweet_id=reply_tweet_id,
                    reply_content=reply_text,
                    reply_type=reply_type,
                    replied_at=datetime.now(UTC).isoformat(),
                    posting_method=posting_method,
                )
            )
            state_manager.record_posting_method(posting_method)


@app.command(name="reply-status")
def reply_status(
    config_path: Annotated[
        Path | None, typer.Option("--config", "-c", help="Config file")
    ] = None,
) -> None:
    """Show reply bot status and today's replies."""
    settings = get_config(config_path)
    state_manager = StateManager(settings.state_file)

    console.print("\n[bold]Reply Bot Status[/bold]\n")

    # Config
    config_table = Table(title="Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value")

    enabled_str = "[green]Yes[/green]" if settings.reply.enabled else "[red]No[/red]"
    config_table.add_row("Enabled", enabled_str)
    config_table.add_row("Max replies/day", str(settings.reply.max_per_day))
    config_table.add_row("Min delay (sec)", str(settings.reply.min_delay_seconds))
    config_table.add_row("Score threshold", f"{settings.reply.score_threshold:.2f}")
    config_table.add_row("Watch interval", f"{settings.reply.watch_interval_seconds}s")
    config_table.add_row("Cookies path", settings.reply.cookies_path)

    console.print(config_table)

    # Today's stats
    today_count = state_manager.get_replies_today_count(settings.schedule.timezone)
    state = state_manager.load()

    stats_table = Table(title="\nToday's Stats")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value")

    stats_table.add_row("Replies today", f"{today_count}/{settings.reply.max_per_day}")
    stats_table.add_row("Total replies (all time)", str(len(state.replied_tweets)))
    stats_table.add_row("Last reply", state.last_reply_at or "Never")

    # Can reply now?
    can_reply = state_manager.can_reply_now(settings.reply.min_delay_seconds)
    can_str = "[green]Yes[/green]" if can_reply else "[yellow]Waiting[/yellow]"
    stats_table.add_row("Can reply now", can_str)

    console.print(stats_table)

    # Recent replies
    recent = state_manager.get_recent_replies(5)
    if recent:
        console.print("\n[bold]Recent Replies[/bold]")
        for reply in reversed(recent):
            console.print(f"\n  [dim]{reply.replied_at}[/dim]")
            console.print(f"  To @{reply.original_author}: {reply.original_content[:50]}...")
            console.print(f"  [green]↳[/green] ({reply.reply_type}) {reply.reply_content[:60]}...")

    # Reply type distribution
    if state.reply_type_history:
        console.print("\n[bold]Reply Type Distribution (last 20)[/bold]")
        recent_types = state.reply_type_history[-20:]
        from collections import Counter

        counts = Counter(recent_types)
        for rtype in ["witty", "agree_twist", "hot_take", "one_liner", "flex"]:
            count = counts.get(rtype, 0)
            bar = "█" * count
            console.print(f"  {rtype:12} {bar} ({count})")


@app.command()
def export_cookies(
    browser: str = typer.Option(
        "chrome",
        "--browser",
        "-b",
        help="Browser to export from (chrome, firefox, edge, safari)",
    ),
    config_path: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Config file"),
    ] = None,
) -> None:
    """Export Twitter cookies from your browser (no login needed)."""
    import json

    try:
        import browser_cookie3
    except ImportError:
        console.print("[red]Error:[/red] browser_cookie3 not installed")
        console.print("Run: uv add browser-cookie3")
        raise typer.Exit(EXIT_ERROR)

    settings = get_config(config_path)
    cookies_path = Path(settings.reply.cookies_path).expanduser()
    cookies_path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"[blue]Exporting Twitter cookies from {browser}...[/blue]")
    console.print("[dim]Make sure the browser is closed for best results.[/dim]\n")

    try:
        # Get browser cookie jar
        if browser == "chrome":
            cj = browser_cookie3.chrome(domain_name=".x.com")
        elif browser == "firefox":
            cj = browser_cookie3.firefox(domain_name=".x.com")
        elif browser == "edge":
            cj = browser_cookie3.edge(domain_name=".x.com")
        elif browser == "safari":
            cj = browser_cookie3.safari(domain_name=".x.com")
        else:
            console.print(f"[red]Unknown browser:[/red] {browser}")
            raise typer.Exit(EXIT_ERROR)

        # Convert to Playwright format
        playwright_cookies = []
        for cookie in cj:
            playwright_cookies.append({
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
                "expires": cookie.expires or -1,
                "httpOnly": bool(cookie._rest.get("HttpOnly", False)),
                "secure": cookie.secure,
                "sameSite": "Lax",
            })

        if not playwright_cookies:
            # Also try twitter.com domain
            if browser == "chrome":
                cj = browser_cookie3.chrome(domain_name=".twitter.com")
            elif browser == "firefox":
                cj = browser_cookie3.firefox(domain_name=".twitter.com")
            elif browser == "edge":
                cj = browser_cookie3.edge(domain_name=".twitter.com")
            elif browser == "safari":
                cj = browser_cookie3.safari(domain_name=".twitter.com")

            for cookie in cj:
                playwright_cookies.append({
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "expires": cookie.expires or -1,
                    "httpOnly": bool(cookie._rest.get("HttpOnly", False)),
                    "secure": cookie.secure,
                    "sameSite": "Lax",
                })

        if not playwright_cookies:
            console.print("[red]No Twitter cookies found![/red]")
            console.print("\nMake sure you are logged into Twitter/X in your browser.")
            raise typer.Exit(EXIT_ERROR)

        # Check for auth cookie
        auth_cookies = [c for c in playwright_cookies if c["name"] in ("auth_token", "ct0")]
        if len(auth_cookies) < 2:
            console.print("[yellow]Warning:[/yellow] Missing some auth cookies.")
            console.print("You may need to log in again in your browser.")

        # Save cookies
        cookies_path.write_text(json.dumps(playwright_cookies, indent=2))
        console.print(f"[green]Exported {len(playwright_cookies)} cookies![/green]")
        console.print(f"Saved to: {cookies_path}")

        # Show key cookies found
        cookie_names = {c["name"] for c in playwright_cookies}
        key_cookies = ["auth_token", "ct0", "twid"]
        found = [c for c in key_cookies if c in cookie_names]
        console.print(f"\nKey cookies found: {', '.join(found) or 'none'}")

        if "auth_token" in cookie_names:
            console.print("\n[green]Ready to use![/green] Run:")
            console.print("  [cyan]uv run twitter-bot reply-once --dry-run[/cyan]")
        else:
            console.print("\n[yellow]Missing auth_token - you may need to log in to Twitter first.[/yellow]")

    except PermissionError:
        console.print("[red]Permission denied![/red]")
        console.print(f"\nClose {browser.title()} completely and try again.")
        console.print("On macOS, you may need to grant Terminal full disk access:")
        console.print("  System Settings → Privacy & Security → Full Disk Access")
        raise typer.Exit(EXIT_ERROR)
    except Exception as e:
        console.print(f"[red]Error exporting cookies:[/red] {e}")
        raise typer.Exit(EXIT_ERROR)


if __name__ == "__main__":
    app()

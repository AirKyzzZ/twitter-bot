"""Tests for state manager title persistence."""

import json
from pathlib import Path
from twitter_bot.state.manager import StateManager

def test_record_and_load_source_title(tmp_path):
    """Test recording a tweet with source title and loading it back."""
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)
    
    # Record a tweet with a source title
    manager.record_tweet(
        tweet_id="123",
        content="Test tweet",
        source_url="http://example.com",
        source_title="Original Article Title"
    )
    
    # Load state and verify
    state = manager.load()
    assert len(state.posted_tweets) == 1
    assert state.posted_tweets[0].source_title == "Original Article Title"

def test_backward_compatibility(tmp_path):
    """Test loading a legacy state file (without source_title)."""
    state_file = tmp_path / "legacy_state.json"
    
    # Create legacy JSON content
    legacy_data = {
        "posted_tweets": [
            {
                "tweet_id": "old_1",
                "content": "Old tweet",
                "content_hash": "hash1",
                "source_url": "http://old.com",
                "posted_at": "2024-01-01T00:00:00"
            }
        ],
        "content_hashes": ["hash1"],
        "processed_urls": ["http://old.com"],
        "last_run": None
    }
    
    with open(state_file, "w") as f:
        json.dump(legacy_data, f)
        
    manager = StateManager(state_file)
    state = manager.load()
    
    assert len(state.posted_tweets) == 1
    assert state.posted_tweets[0].tweet_id == "old_1"
    assert state.posted_tweets[0].source_title is None
